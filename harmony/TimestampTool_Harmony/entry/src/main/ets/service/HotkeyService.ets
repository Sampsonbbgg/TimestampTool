/**
 * 全局快捷键后台监听服务
 *
 * 使用 @ohos.multimodalInput.inputConsumer 注册全局组合键 Ctrl+Shift+Z。
 * 当用户在任意应用按下快捷键时，通过 Emitter 通知前台弹出模板选择浮窗。
 *
 * 权限依赖：ohos.permission.INPUT_MONITORING
 */

import ServiceExtensionAbility from '@ohos.app.ability.ServiceExtensionAbility';
import inputConsumer from '@ohos.multimodalInput.inputConsumer';
import emitter from '@ohos.events.emitter';
import Want from '@ohos.app.ability.Want';

// 全局快捷键事件ID（用于 Emitter 通信）
export const HOTKEY_TRIGGER_EVENT_ID = 10001;

export default class HotkeyService extends ServiceExtensionAbility {
  private hotkeyRegistered: boolean = false;

  onCreate(want: Want): void {
    console.info('[HotkeyService] 服务创建');
    this.registerGlobalHotkey();
  }

  onRequest(want: Want, startId: number): void {
    console.info('[HotkeyService] 收到启动请求');
  }

  onDestroy(): void {
    console.info('[HotkeyService] 服务销毁');
    this.unregisterGlobalHotkey();
  }

  /**
   * 注册全局快捷键 Ctrl+Shift+Z
   *
   * inputConsumer.on('key') 允许在系统级别监听组合键，
   * 即使其他应用在前台也能捕获。
   */
  private registerGlobalHotkey(): void {
    try {
      // 定义快捷键组合：Ctrl + Shift + Z
      const keyCombination: inputConsumer.KeyOptions = {
        preKeys: [2072, 2047],  // Ctrl(2072) + Shift(2047) 的 keyCode
        finalKey: 2050,         // Z 键的 keyCode
        isFinalKeyDown: true,
        finalKeyDownDuration: 0,
      };

      inputConsumer.on('key', keyCombination, (keyOptions) => {
        console.info('[HotkeyService] 快捷键触发！');
        // 通过 Emitter 通知前台 UI 弹出模板菜单
        emitter.emit({ eventId: HOTKEY_TRIGGER_EVENT_ID }, { data: {} });
      });

      this.hotkeyRegistered = true;
      console.info('[HotkeyService] 全局快捷键 Ctrl+Shift+Z 注册成功');
    } catch (error) {
      console.error('[HotkeyService] 快捷键注册失败:', JSON.stringify(error));
    }
  }

  /**
   * 注销全局快捷键
   */
  private unregisterGlobalHotkey(): void {
    if (!this.hotkeyRegistered) return;
    try {
      const keyCombination: inputConsumer.KeyOptions = {
        preKeys: [2072, 2047],
        finalKey: 2050,
        isFinalKeyDown: true,
        finalKeyDownDuration: 0,
      };
      inputConsumer.off('key', keyCombination);
      this.hotkeyRegistered = false;
      console.info('[HotkeyService] 全局快捷键已注销');
    } catch (error) {
      console.error('[HotkeyService] 快捷键注销失败:', JSON.stringify(error));
    }
  }
}
