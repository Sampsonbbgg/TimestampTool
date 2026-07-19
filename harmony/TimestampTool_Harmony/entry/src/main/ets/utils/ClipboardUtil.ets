/**
 * 剪贴板工具 - 写入系统剪贴板并提示粘贴
 *
 * 使用 @ohos.pasteboard API 将格式化后的文本写入系统剪贴板。
 * PC 端用户收到 toast 提示后按 Ctrl+V 粘贴到当前焦点位置。
 */

import pasteboard from '@ohos.pasteboard';
import promptAction from '@ohos.promptAction';

export class ClipboardUtil {
  /**
   * 将文本写入系统剪贴板并提示用户粘贴
   *
   * @param text 要写入的文本内容
   * @param showToast 是否显示提示（默认 true）
   */
  static async copyAndNotify(text: string, showToast: boolean = true): Promise<boolean> {
    try {
      // 创建纯文本剪贴板数据
      const pasteData = pasteboard.createData(pasteboard.MIMETYPE_TEXT_PLAIN, text);
      // 获取系统剪贴板实例
      const systemPasteboard = pasteboard.getSystemPasteboard();
      // 写入剪贴板
      await systemPasteboard.setData(pasteData);

      // 提示用户粘贴
      if (showToast) {
        promptAction.showToast({
          message: '已复制，按 Ctrl+V 粘贴',
          duration: 1500,
        });
      }

      return true;
    } catch (error) {
      console.error('[ClipboardUtil] 写入剪贴板失败:', JSON.stringify(error));
      promptAction.showToast({
        message: '复制失败，请重试',
        duration: 2000,
      });
      return false;
    }
  }

  /**
   * 读取当前剪贴板纯文本内容
   */
  static async readText(): Promise<string> {
    try {
      const systemPasteboard = pasteboard.getSystemPasteboard();
      const pasteData = await systemPasteboard.getData();
      if (pasteData.hasType(pasteboard.MIMETYPE_TEXT_PLAIN)) {
        const record = pasteData.getPrimaryText();
        return record ?? '';
      }
      return '';
    } catch {
      return '';
    }
  }
}
