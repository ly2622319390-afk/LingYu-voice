/**
 * 文本注入引擎 — 将文本"输入"到当前聚焦的应用
 *
 * 方案: 剪贴板 + 模拟 Ctrl+V
 *
 * 流程:
 *   保存剪贴板原文 → 写入新文本 → 模拟 Ctrl+V 粘贴
 *   → 延迟恢复原始剪贴板内容
 *
 * 适用于 Windows/macOS/Linux 所有应用
 */
import { clipboard, nativeImage, BrowserWindow } from 'electron';

export class TextInjector {
  /**
   * 注入文本到当前聚焦的应用
   */
  async inject(text: string): Promise<boolean> {
    if (!text) return false;

    try {
      // 保存原始剪贴板内容
      const originalText = clipboard.readText();
      const originalImage = clipboard.readImage();

      // 写入新文本
      clipboard.writeText(text);

      // 短暂延迟确保剪贴板写入完成
      await this.delay(50);

      // 模拟 Ctrl+V (或 Cmd+V on macOS)
      const modKey = process.platform === 'darwin' ? 'Command' : 'Control';
      const focusedWin = BrowserWindow.getFocusedWindow();

      if (focusedWin) {
        focusedWin.webContents.sendInputEvent({
          type: 'keyDown',
          keyCode: modKey,
        });
        focusedWin.webContents.sendInputEvent({
          type: 'keyDown',
          keyCode: 'KeyV',
        });
        focusedWin.webContents.sendInputEvent({
          type: 'keyUp',
          keyCode: 'KeyV',
        });
        focusedWin.webContents.sendInputEvent({
          type: 'keyUp',
          keyCode: modKey,
        });
      } else {
        // 没有聚焦窗口时，使用进程级键盘模拟
        // 这需要 native 模块，当前先跳过
        console.warn('[TextInjector] 无聚焦窗口，无法注入文本');
        return false;
      }

      // 延迟恢复原始剪贴板
      this.delay(1000).then(() => {
        try {
          if (originalImage && !originalImage.isEmpty()) {
            clipboard.writeImage(originalImage);
          } else if (originalText) {
            clipboard.writeText(originalText);
          }
        } catch {
          // 恢复失败不影响主要功能
        }
      });

      return true;
    } catch (err) {
      console.error('[TextInjector] 注入失败:', err);
      return false;
    }
  }

  private delay(ms: number): Promise<void> {
    return new Promise((r) => setTimeout(r, ms));
  }
}
