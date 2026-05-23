/**
 * 文本注入引擎 — 将文本"输入"到当前聚焦的外部应用
 *
 * 两阶段设计:
 *   1. prepare(text) — 保存原始剪贴板，写入新文本
 *   2. paste()       — 操作系统级 Ctrl+V，延迟恢复剪贴板
 *
 * 主进程 IPC 处理器负责在 prepare 和 paste 之间隐藏浮窗，
 * 确保焦点回到外部应用后再模拟粘贴。
 */
import { clipboard } from 'electron';
import { exec } from 'child_process';

export class TextInjector {
  private savedText = '';
  private savedImage: Electron.NativeImage | null = null;

  /**
   * 第一阶段：保存原始剪贴板，写入目标文本
   */
  prepare(text: string): void {
    if (!text) return;
    this.savedText = clipboard.readText();
    this.savedImage = clipboard.readImage();
    clipboard.writeText(text);
  }

  /**
   * 第二阶段：操作系统级模拟粘贴，延迟恢复剪贴板
   *
   * 调用前必须确保：
   *   - prepare() 已被调用
   *   - 浮窗已隐藏，焦点已回到目标外部应用
   */
  async paste(): Promise<boolean> {
    try {
      // 短暂等待剪贴板 + 焦点切换就绪
      await this.delay(80);

      const ok = await this.osPaste();

      // 延迟恢复原始剪贴板
      this.delay(1200).then(() => this.restoreClipboard());

      return ok;
    } catch (err) {
      console.error('[TextInjector] 粘贴失败:', err);
      return false;
    }
  }

  /**
   * 恢复剪贴板为原始内容
   */
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

  /**
   * 操作系统级模拟粘贴（Ctrl+V / Cmd+V）
   *
   * Windows: PowerShell SendKeys（最可靠，支持所有 Win32 应用）
   * macOS:   osascript AppleScript
   * Linux:   xdotool
   */
  private osPaste(): Promise<boolean> {
    return new Promise((resolve) => {
      let command: string;

      switch (process.platform) {
        case 'win32':
          command =
            'powershell -Command "Add-Type -AssemblyName System.Windows.Forms; ' +
            '[System.Windows.Forms.SendKeys]::SendWait(\'^v\')"';
          break;
        case 'darwin':
          command =
            'osascript -e \'tell application "System Events" to keystroke "v" using command down\'';
          break;
        case 'linux':
          command = 'xdotool key ctrl+v';
          break;
        default:
          console.warn('[TextInjector] 不支持的平台:', process.platform);
          resolve(false);
          return;
      }

      exec(command, { timeout: 3000 }, (error, _stdout, stderr) => {
        if (error) {
          console.warn('[TextInjector] 模拟粘贴失败:', error.message, stderr);
          resolve(false);
        } else {
          resolve(true);
        }
      });
    });
  }

  private delay(ms: number): Promise<void> {
    return new Promise((r) => setTimeout(r, ms));
  }
}
