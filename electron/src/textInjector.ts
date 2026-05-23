/**
 * 文本注入引擎 — 将文本"输入"到当前聚焦的外部应用
 *
 * 核心策略（最流畅方案）:
 *   1. captureTargetWindow() — 语音开始前，记录当前前台窗口的句柄 (HWND)
 *   2. prepare(text) — 保存原始剪贴板，写入目标文本
 *   3. pasteToTarget() — 将目标窗口置前，操作系统级 Ctrl+V，恢复剪贴板
 *
 * 无需猜测焦点恢复行为，全程精确控制目标窗口。
 */
import { clipboard } from 'electron';
import { exec } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

export class TextInjector {
  /** 目标窗口句柄（十进制字符串，如 "987654"） */
  private targetHwnd = '';
  private savedText = '';
  private savedImage: Electron.NativeImage | null = null;

  // ─── 目标窗口捕获 ──────────────────────────────────────────────

  /**
   * 捕获当前前台窗口句柄
   * 在浮窗显示前调用（用户已选好文本框后，按快捷键前）
   */
  async captureTargetWindow(): Promise<boolean> {
    const script = `Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class WinAPI {
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
}
'@
write-host ([WinAPI]::GetForegroundWindow())`;

    const hwnd = await this.runPowerShell(script);
    if (hwnd) {
      this.targetHwnd = hwnd;
      console.log('[TextInjector] 已捕获目标窗口:', hwnd);
      return true;
    }
    console.warn('[TextInjector] 未能捕获目标窗口');
    return false;
  }

  // ─── 剪贴板管理 ───────────────────────────────────────────────

  prepare(text: string): void {
    if (!text) return;
    this.savedText = clipboard.readText();
    this.savedImage = clipboard.readImage();
    clipboard.writeText(text);
  }

  private restoreClipboard(): void {
    try {
      if (this.savedImage && !this.savedImage.isEmpty()) {
        clipboard.writeImage(this.savedImage);
      } else if (this.savedText) {
        clipboard.writeText(this.savedText);
      }
    } catch {
      // 恢复失败不影响主要功能
    }
    this.savedText = '';
    this.savedImage = null;
  }

  // ─── 粘贴到目标窗口 ────────────────────────────────────────────

  /**
   * 将文本粘贴到之前捕获的目标窗口
   *
   * 流程:
   *   SetForegroundWindow(HWND) → 等待焦点切换 → SendKeys('^v')
   *
   * 调用前需确保：
   *   - prepare(text) 已调用（文本已在剪贴板）
   *   - 浮窗已隐藏
   */
  async pasteToTarget(): Promise<boolean> {
    if (!this.targetHwnd) {
      console.warn('[TextInjector] 无目标窗口句柄，改用常规方式');
      return this.pasteFallback();
    }

    const script = `
param([string]$hwndStr)

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class WinAPI {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
}
'@

Add-Type -AssemblyName System.Windows.Forms

$hwnd = [IntPtr]::Parse($hwndStr)
[WinAPI]::SetForegroundWindow($hwnd)
Start-Sleep -Milliseconds 80
[System.Windows.Forms.SendKeys]::SendWait('^v')
write-host "ok"
`.trim();

    try {
      const result = await this.runPowerShellWithArg(script, this.targetHwnd);
      const ok = result === 'ok';
      this.scheduleRestore();
      return ok;
    } catch (err) {
      console.error('[TextInjector] 目标粘贴失败:', err);
      this.scheduleRestore();
      return false;
    }
  }

  /**
   * 备用方案：不使用目标窗口句柄，仅发送 OS 级 Ctrl+V。
   * 用于未捕获到句柄或句柄失效时的降级。
   */
  private async pasteFallback(): Promise<boolean> {
    const script = `Add-Type -AssemblyName System.Windows.Forms
Start-Sleep -Milliseconds 50
[System.Windows.Forms.SendKeys]::SendWait('^v')
write-host "ok"`;

    try {
      const result = await this.runPowerShell(script);
      const ok = result === 'ok';
      this.scheduleRestore();
      return ok;
    } catch (err) {
      console.error('[TextInjector] 备用粘贴失败:', err);
      this.scheduleRestore();
      return false;
    }
  }

  /** 延迟恢复原始剪贴板 */
  private scheduleRestore(): void {
    setTimeout(() => this.restoreClipboard(), 1200);
  }

  // ─── PowerShell 执行 ──────────────────────────────────────────

  /**
   * 执行不含参数的内联 PowerShell 脚本
   */
  private runPowerShell(script: string): Promise<string> {
    const tmpFile = path.join(os.tmpdir(), `vi_cap_${Date.now()}_${Math.random().toString(36).slice(2, 8)}.ps1`);
    fs.writeFileSync(tmpFile, script, 'utf8');

    return new Promise((resolve, reject) => {
      exec(
        `powershell -NoProfile -ExecutionPolicy Bypass -File "${tmpFile}"`,
        { timeout: 5000, windowsHide: true },
        (error, stdout) => {
          this.cleanupTemp(tmpFile);
          if (error) {
            reject(new Error(stdout || error.message));
          } else {
            resolve(stdout.trim());
          }
        },
      );
    });
  }

  /**
   * 执行带参数的 PowerShell 脚本
   */
  private runPowerShellWithArg(script: string, arg: string): Promise<string> {
    const tmpFile = path.join(os.tmpdir(), `vi_paste_${Date.now()}_${Math.random().toString(36).slice(2, 8)}.ps1`);
    fs.writeFileSync(tmpFile, script, 'utf8');

    return new Promise((resolve, reject) => {
      exec(
        `powershell -NoProfile -ExecutionPolicy Bypass -File "${tmpFile}" "${arg}"`,
        { timeout: 5000, windowsHide: true },
        (error, stdout) => {
          this.cleanupTemp(tmpFile);
          if (error) {
            reject(new Error(stdout || error.message));
          } else {
            resolve(stdout.trim());
          }
        },
      );
    });
  }

  private cleanupTemp(file: string): void {
    try { fs.unlinkSync(file); } catch { /* ignore */ }
  }
}
