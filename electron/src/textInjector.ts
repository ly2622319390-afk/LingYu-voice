/**
 * 文本注入引擎 — 将文本"输入"到当前聚焦的外部应用
 *
 * 方案演进:
 *   1st: Electron sendInputEvent → 只对 Electron 自身窗口生效（失败）
 *   2nd: PowerShell SendKeys → 被执行策略/杀软限制（失败）
 *   3rd: C# 编译辅助程序 + AttachThreadInput + SendInput（当前）
 *
 * 当前方案:
 *   编译一个 C# 辅助程序 (PasteHelper.exe)，通过 Windows API
 *   AttachThreadInput + SetForegroundWindow + SendInput 实现
 *   跨进程文本注入，绕过所有权限限制。
 */
import { clipboard } from 'electron';
import { exec } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

export class TextInjector {
  private targetHwnd = '';
  private savedText = '';
  private savedImage: Electron.NativeImage | null = null;
  private pasteHelperExe = '';

  private readonly CSC_PATHS = [
    'C:\\Windows\\Microsoft.NET\\Framework64\\v4.0.30319\\csc.exe',
    'C:\\Windows\\Microsoft.NET\\Framework\\v4.0.30319\\csc.exe',
  ];

  /** 窗口标题（调试用） */
  private targetTitle = '';

  // ─── 初始化 ──────────────────────────────────────────────────

  constructor() {
    // 辅助 exe 缓存在用户临时目录
    this.pasteHelperExe = path.join(os.tmpdir(), 'vi_paste_helper.exe');
  }

  /**
   * 确保辅助程序已编译
   * 程序: PasteHelper.exe — 接收 HWND 参数，唤回窗口后发送 Ctrl+V
   */
  async ensureHelper(): Promise<boolean> {
    // 检查是否已编译
    if (fs.existsSync(this.pasteHelperExe)) return true;

    const csPath = await this.findCsc();
    if (!csPath) {
      console.warn('[TextInjector] 未找到 C# 编译器 (csc.exe)');
      return false;
    }

    const sourcePath = path.join(os.tmpdir(), 'vi_paste_helper.cs');
    const source = [
      'using System;',
      'using System.Runtime.InteropServices;',
      'using System.Windows.Forms;',
      'class PasteHelper {',
      '  [DllImport("user32.dll")]',
      '  static extern uint GetWindowThreadProcessId(IntPtr hWnd, IntPtr lpdwProcessId);',
      '  [DllImport("kernel32.dll")]',
      '  static extern uint GetCurrentThreadId();',
      '  [DllImport("user32.dll")]',
      '  static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);',
      '  [DllImport("user32.dll")]',
      '  static extern bool SetForegroundWindow(IntPtr hWnd);',
      '  [DllImport("user32.dll")]',
      '  static extern IntPtr GetForegroundWindow();',
      '  [DllImport("user32.dll")]',
      '  static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);',
      '  static void Main(string[] a) {',
      '    if (a.Length > 0 && long.TryParse(a[0], out long h)) {',
      '      IntPtr hwnd = new IntPtr(h);',
      '      StringBuilder sb = new StringBuilder(256);',
      '      GetWindowText(hwnd, sb, 256);',
      '      uint tt = GetWindowThreadProcessId(hwnd, IntPtr.Zero);',
      '      uint ct = GetCurrentThreadId();',
      '      AttachThreadInput(ct, tt, true);',
      '      SetForegroundWindow(hwnd);',
      '      AttachThreadInput(ct, tt, false);',
      '      System.Threading.Thread.Sleep(100);',
      '    }',
      '    SendKeys.SendWait("^v");',
      '  }',
      '}',
    ].join('\n');

    fs.writeFileSync(sourcePath, source, 'utf8');

    return new Promise((resolve) => {
      exec(
        `"${csPath}" /nologo /reference:System.Windows.Forms.dll /target:exe /out:"${this.pasteHelperExe}" "${sourcePath}"`,
        { timeout: 30000, windowsHide: true },
        (error, stdout, stderr) => {
          try { fs.unlinkSync(sourcePath); } catch { /* ignore */ }
          if (error) {
            console.error('[TextInjector] 编译 PasteHelper 失败:', error.message, stderr);
            resolve(false);
          } else {
            console.log('[TextInjector] PasteHelper 编译成功');
            resolve(true);
          }
        },
      );
    });
  }

  private findCsc(): Promise<string> {
    for (const p of this.CSC_PATHS) {
      if (fs.existsSync(p)) return Promise.resolve(p);
    }
    return Promise.resolve('');
  }

  // ─── 目标窗口捕获 ──────────────────────────────────────────────

  async captureTargetWindow(): Promise<boolean> {
    // 方法1: 通过 Powershell 获取 HWND + 窗口标题
    const psScript = [
      'Add-Type -TypeDefinition @\'',
      'using System;',
      'using System.Runtime.InteropServices;',
      'using System.Text;',
      'public class WinAPI {',
      '    [DllImport("user32.dll")]',
      '    public static extern IntPtr GetForegroundWindow();',
      '    [DllImport("user32.dll")]',
      '    public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);',
      '}',
      '\'@',
      '$hwnd = [WinAPI]::GetForegroundWindow()',
      '$sb = New-Object System.Text.StringBuilder 256',
      '[WinAPI]::GetWindowText($hwnd, $sb, 256) | Out-Null',
      '# 输出格式: HWND|WindowTitle',
      'Write-Output ($hwnd.ToInt64().ToString() + "|" + $sb.ToString())',
    ].join('\n');

    const tmpFile = this.tempFile('cap');
    fs.writeFileSync(tmpFile, psScript, 'utf8');

    return new Promise((resolve) => {
      exec(
        `powershell -NoProfile -ExecutionPolicy Bypass -File "${tmpFile}"`,
        { timeout: 5000, windowsHide: true },
        (error, stdout) => {
          this.cleanupTemp(tmpFile);
          const line = (stdout || '').trim().split('\n')[0] || '';
          const pipeIdx = line.indexOf('|');
          if (pipeIdx > 0) {
            this.targetHwnd = line.substring(0, pipeIdx);
            this.targetTitle = line.substring(pipeIdx + 1);
            console.log('[TextInjector] 已捕获: HWND=' + this.targetHwnd + ', Title=' + this.targetTitle);
            return resolve(true);
          }
          console.warn('[TextInjector] 捕获失败, stdout="' + stdout.trim() + '"');
          resolve(false);
        },
      );
    });
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
    } catch { /* ignore */ }
    this.savedText = '';
    this.savedImage = null;
  }

  // ─── 粘贴 ─────────────────────────────────────────────────────

  async pasteToTarget(): Promise<boolean> {
    // 尝试3种方法，任一成功即可
    if (await this.pasteViaHelper()) return true;
    console.warn('[TextInjector] 辅助程序失败，尝试 PowerShell 备用');
    if (await this.pasteViaPowerShell()) return true;
    console.warn('[TextInjector] PowerShell 也失败');
    return false;
  }

  /** 方法1: C# 辅助程序 (PasteHelper.exe) — 最可靠 */
  private async pasteViaHelper(): Promise<boolean> {
    if (!this.targetHwnd) return false;
    if (!fs.existsSync(this.pasteHelperExe)) {
      const ok = await this.ensureHelper();
      if (!ok) return false;
    }
    return new Promise((resolve) => {
      exec(
        `"${this.pasteHelperExe}" "${this.targetHwnd}"`,
        { timeout: 5000, windowsHide: true },
        (error) => {
          if (error) {
            console.warn('[TextInjector] Helper 执行失败:', error.message);
            resolve(false);
          } else {
            this.scheduleRestore();
            resolve(true);
          }
        },
      );
    });
  }

  /** 方法2: PowerShell 备用 */
  private async pasteViaPowerShell(): Promise<boolean> {
    const tmpFile = this.tempFile('fallback');
    const script = [
      'Add-Type -TypeDefinition @\'',
      'using System;',
      'using System.Runtime.InteropServices;',
      'public class WinAPI2 {',
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
      'Add-Type -AssemblyName System.Windows.Forms',
      // READ HWND FROM ARG
      '$hwndStr = $args[0]',
      'if ($hwndStr) {',
      '  $hwnd = [IntPtr]::new([long]::Parse($hwndStr))',
      '  $tt = [WinAPI2]::GetWindowThreadProcessId($hwnd, [IntPtr]::Zero)',
      '  $ct = [WinAPI2]::GetCurrentThreadId()',
      '  [WinAPI2]::AttachThreadInput($ct, $tt, $true)',
      '  [WinAPI2]::SetForegroundWindow($hwnd)',
      '  [WinAPI2]::AttachThreadInput($ct, $tt, $false)',
      '  Start-Sleep -Milliseconds 100',
      '}',
      '[System.Windows.Forms.SendKeys]::SendWait("^v")',
      'Write-Output "ok"',
    ].join('\n');

    fs.writeFileSync(tmpFile, script, 'utf8');

    return new Promise((resolve) => {
      exec(
        `powershell -NoProfile -ExecutionPolicy Bypass -File "${tmpFile}" "${this.targetHwnd}"`,
        { timeout: 5000, windowsHide: true },
        (error, stdout) => {
          this.cleanupTemp(tmpFile);
          const ok = !error && stdout.trim() === 'ok';
          if (ok) this.scheduleRestore();
          resolve(ok);
        },
      );
    });
  }

  private scheduleRestore(): void {
    setTimeout(() => this.restoreClipboard(), 1200);
  }

  // ─── 工具函数 ────────────────────────────────────────────────

  private tempFile(prefix: string): string {
    return path.join(os.tmpdir(), `vi_${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}.ps1`);
  }

  private cleanupTemp(file: string): void {
    try { fs.unlinkSync(file); } catch { /* ignore */ }
  }
}
