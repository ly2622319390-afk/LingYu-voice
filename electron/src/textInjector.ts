/**
 * 文本注入引擎 — 将文本"输入"到当前聚焦的外部应用
 *
 * 核心策略:
 *   1. captureTargetWindow() — 语音开始前，记录当前前台窗口句柄 (HWND)
 *   2. prepare(text) — 保存原始剪贴板，写入目标文本
 *   3. pasteToTarget() — AttachThreadInput + SetForegroundWindow + SendKeys
 *
 * 注意: PowerShell 中必须用 Write-Output 而非 Write-Host，
 *       write-host 输出到信息流 (stream 6) 而非 stdout (stream 1)，
 *       Node.js exec 的 stdout 捕获不到 write-host 的结果。
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
    const script = [
      'Add-Type -TypeDefinition @\'',
      'using System;',
      'using System.Runtime.InteropServices;',
      'public class WinAPI {',
      '    [DllImport("user32.dll")]',
      '    public static extern IntPtr GetForegroundWindow();',
      '}',
      '\'@',
      '# 必须用 Write-Output，不能用 Write-Host（后者不进 stdout）',
      'Write-Output ([WinAPI]::GetForegroundWindow().ToInt64())',
    ].join('\n');

    const hwnd = await this.runPowerShell(script);
    if (hwnd && hwnd !== '0') {
      this.targetHwnd = hwnd;
      console.log('[TextInjector] 已捕获目标窗口 HWND:', hwnd);
      return true;
    }
    console.warn('[TextInjector] 未能捕获目标窗口, stdout="' + hwnd + '"');
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
   * 核心技巧:
   *   1. AttachThreadInput — 绕过 Windows SetForegroundWindow 权限限制
   *   2. SetForegroundWindow — 把目标窗口拉到前台
   *   3. SendKeys — 发送 Ctrl+V
   *
   * 调用前需确保 prepare(text) 已调用，浮窗已隐藏。
   */
  async pasteToTarget(): Promise<boolean> {
    if (!this.targetHwnd) {
      console.warn('[TextInjector] 无目标窗口句柄，改用备用粘贴');
      return this.pasteFallback();
    }

    const script = [
      'param([string]$hwndStr)',
      '',
      'Add-Type -TypeDefinition @\'',
      'using System;',
      'using System.Runtime.InteropServices;',
      'public class WinAPI {',
      '    [DllImport("user32.dll")]',
      '    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, IntPtr lpdwProcessId);',
      '    [DllImport("kernel32.dll")]',
      '    public static extern uint GetCurrentThreadId();',
      '    [DllImport("user32.dll")]',
      '    public static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);',
      '    [DllImport("user32.dll")]',
      '    public static extern bool SetForegroundWindow(IntPtr hWnd);',
      '}',
      '\'@',
      '',
      'Add-Type -AssemblyName System.Windows.Forms',
      '',
      '$hwnd = [IntPtr]::new([Int64]::Parse($hwndStr))',
      '',
      '# AttachThreadInput 绕过 SetForegroundWindow 权限限制',
      '$targetThread = [WinAPI]::GetWindowThreadProcessId($hwnd, [IntPtr]::Zero)',
      '$currentThread = [WinAPI]::GetCurrentThreadId()',
      '[WinAPI]::AttachThreadInput($currentThread, $targetThread, $true)',
      '[WinAPI]::SetForegroundWindow($hwnd)',
      '[WinAPI]::AttachThreadInput($currentThread, $targetThread, $false)',
      '',
      'Start-Sleep -Milliseconds 100',
      '[System.Windows.Forms.SendKeys]::SendWait("^v")',
      '',
      'Write-Output "ok"',
    ].join('\n');

    try {
      const result = await this.runPowerShellWithArg(script, this.targetHwnd);
      const ok = result.trim() === 'ok';
      if (!ok) console.warn('[TextInjector] pasteToTarget 返回值异常:', result);
      this.scheduleRestore();
      return ok;
    } catch (err) {
      console.error('[TextInjector] 目标粘贴异常:', err);
      this.scheduleRestore();
      return false;
    }
  }

  /**
   * 备用方案：隐藏浮窗后用 SendKeys 直接发送 Ctrl+V。
   * 不指定目标窗口（粘贴到当前焦点窗口）。
   */
  private async pasteFallback(): Promise<boolean> {
    const script = [
      'Add-Type -AssemblyName System.Windows.Forms',
      'Start-Sleep -Milliseconds 80',
      '[System.Windows.Forms.SendKeys]::SendWait("^v")',
      'Write-Output "ok"',
    ].join('\n');

    try {
      const result = await this.runPowerShell(script);
      const ok = result.trim() === 'ok';
      if (!ok) console.warn('[TextInjector] pasteFallback 返回值异常:', result);
      this.scheduleRestore();
      return ok;
    } catch (err) {
      console.error('[TextInjector] 备用粘贴异常:', err);
      this.scheduleRestore();
      return false;
    }
  }

  /** 延迟恢复原始剪贴板 */
  private scheduleRestore(): void {
    setTimeout(() => this.restoreClipboard(), 1200);
  }

  // ─── PowerShell 执行 ──────────────────────────────────────────

  private runPowerShell(script: string): Promise<string> {
    const tmpFile = this.tempFile('cap');
    fs.writeFileSync(tmpFile, script, 'utf8');

    return new Promise((resolve) => {
      exec(
        `powershell -NoProfile -ExecutionPolicy Bypass -File "${tmpFile}"`,
        { timeout: 5000, windowsHide: true },
        (error, stdout, stderr) => {
          this.cleanupTemp(tmpFile);
          if (error) {
            console.warn('[TextInjector] PS 执行失败:', error.message, stderr);
            resolve('');
          } else {
            resolve(stdout.trim());
          }
        },
      );
    });
  }

  private runPowerShellWithArg(script: string, arg: string): Promise<string> {
    const tmpFile = this.tempFile('paste');
    fs.writeFileSync(tmpFile, script, 'utf8');

    return new Promise((resolve) => {
      exec(
        `powershell -NoProfile -ExecutionPolicy Bypass -File "${tmpFile}" "${arg}"`,
        { timeout: 5000, windowsHide: true },
        (error, stdout, stderr) => {
          this.cleanupTemp(tmpFile);
          if (error) {
            console.warn('[TextInjector] PS 执行失败:', error.message, stderr);
            resolve('');
          } else {
            resolve(stdout.trim());
          }
        },
      );
    });
  }

  private tempFile(prefix: string): string {
    return path.join(os.tmpdir(), `vi_${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}.ps1`);
  }

  private cleanupTemp(file: string): void {
    try { fs.unlinkSync(file); } catch { /* ignore */ }
  }
}
