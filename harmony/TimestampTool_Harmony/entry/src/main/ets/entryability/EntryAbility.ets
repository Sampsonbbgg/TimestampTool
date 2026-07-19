/**
 * TimestampTool 应用入口 Ability
 *
 * 负责：
 * 1. 初始化 ConfigManager（Preferences）
 * 2. 启动后台 HotkeyService（全局快捷键监听）
 * 3. 加载主页面 Index.ets
 */

import UIAbility from '@ohos.app.ability.UIAbility';
import AbilityConstant from '@ohos.app.ability.AbilityConstant';
import Want from '@ohos.app.ability.Want';
import window from '@ohos.window';
import { ConfigManager } from '../model/ConfigManager';

// 全局配置管理实例（供各页面共享）
export let globalConfigManager: ConfigManager;

export default class EntryAbility extends UIAbility {
  async onCreate(want: Want, launchParam: AbilityConstant.LaunchParam): Promise<void> {
    console.info('[EntryAbility] 应用启动');

    // 初始化配置管理
    globalConfigManager = new ConfigManager(this.context);
    await globalConfigManager.init();

    // 启动后台快捷键监听服务
    this.startHotkeyService();
  }

  onWindowStageCreate(windowStage: window.WindowStage): void {
    // 加载主设置页面
    windowStage.loadContent('pages/Index', (err) => {
      if (err.code) {
        console.error('[EntryAbility] 页面加载失败:', JSON.stringify(err));
        return;
      }
      console.info('[EntryAbility] 主页面加载成功');
    });
  }

  onForeground(): void {
    console.info('[EntryAbility] 进入前台');
  }

  onBackground(): void {
    console.info('[EntryAbility] 进入后台（快捷键服务继续运行）');
  }

  onDestroy(): void {
    console.info('[EntryAbility] 应用销毁');
  }

  /**
   * 启动后台快捷键监听服务
   */
  private startHotkeyService(): void {
    try {
      const want: Want = {
        bundleName: 'com.sampson.timestamptool',
        abilityName: 'HotkeyServiceAbility',
      };
      this.context.startServiceExtensionAbility(want).then(() => {
        console.info('[EntryAbility] HotkeyService 启动成功');
      }).catch((err: Error) => {
        console.error('[EntryAbility] HotkeyService 启动失败:', err.message);
      });
    } catch (error) {
      console.error('[EntryAbility] 启动服务异常:', JSON.stringify(error));
    }
  }
}
