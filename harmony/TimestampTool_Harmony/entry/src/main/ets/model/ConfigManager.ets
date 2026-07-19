/**
 * TimestampTool 配置管理 - 使用 @ohos.data.preferences
 *
 * 数据存储在系统 Preferences 中（用户不可见，无外显文件），
 * 与 Windows 版 config.json 语义对齐。
 */

import dataPreferences from '@ohos.data.preferences';
import { TemplateItem, TemplateEngine } from './TemplateEngine';

const PREFERENCES_NAME = 'timestamp_tool_config';
const KEY_TEMPLATES = 'templates';
const KEY_HOTKEY = 'hotkey';
const KEY_AUTOSTART = 'autostart';

const DEFAULT_HOTKEY = 'ctrl+shift+z';

export class ConfigManager {
  private preferences: dataPreferences.Preferences | null = null;
  private context: Context;

  constructor(context: Context) {
    this.context = context;
  }

  /**
   * 初始化（异步，在应用启动时调用）
   */
  async init(): Promise<void> {
    this.preferences = await dataPreferences.getPreferences(this.context, PREFERENCES_NAME);
    // 首次运行时写入默认模板
    const hasTemplates = this.preferences.hasSync(KEY_TEMPLATES);
    if (!hasTemplates) {
      await this.setTemplates(TemplateEngine.getDefaultTemplates());
      await this.setHotkey(DEFAULT_HOTKEY);
      await this.setAutostart(false);
    }
  }

  /**
   * 获取模板列表
   */
  async getTemplates(): Promise<TemplateItem[]> {
    if (!this.preferences) return TemplateEngine.getDefaultTemplates();
    try {
      const raw = this.preferences.getSync(KEY_TEMPLATES, '[]') as string;
      return JSON.parse(raw) as TemplateItem[];
    } catch {
      return TemplateEngine.getDefaultTemplates();
    }
  }

  /**
   * 保存模板列表
   */
  async setTemplates(templates: TemplateItem[]): Promise<void> {
    if (!this.preferences) return;
    this.preferences.putSync(KEY_TEMPLATES, JSON.stringify(templates));
    await this.preferences.flush();
  }

  /**
   * 获取快捷键设置
   */
  getHotkey(): string {
    if (!this.preferences) return DEFAULT_HOTKEY;
    return this.preferences.getSync(KEY_HOTKEY, DEFAULT_HOTKEY) as string;
  }

  /**
   * 保存快捷键设置
   */
  async setHotkey(hotkey: string): Promise<void> {
    if (!this.preferences) return;
    this.preferences.putSync(KEY_HOTKEY, hotkey);
    await this.preferences.flush();
  }

  /**
   * 获取开机自启状态
   */
  getAutostart(): boolean {
    if (!this.preferences) return false;
    return this.preferences.getSync(KEY_AUTOSTART, false) as boolean;
  }

  /**
   * 保存开机自启状态
   */
  async setAutostart(enabled: boolean): Promise<void> {
    if (!this.preferences) return;
    this.preferences.putSync(KEY_AUTOSTART, enabled);
    await this.preferences.flush();
  }

  /**
   * 重置为默认配置
   */
  async resetToDefault(): Promise<void> {
    await this.setTemplates(TemplateEngine.getDefaultTemplates());
    await this.setHotkey(DEFAULT_HOTKEY);
  }
}
