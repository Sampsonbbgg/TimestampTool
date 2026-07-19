/**
 * TimestampTool 主设置页面
 *
 * 三栏式布局：模板管理 / 快捷键设置 / 偏好设置（开机自启）
 * 与 Windows 版设置窗口功能对齐，视觉风格适配 HarmonyOS。
 */

import router from '@ohos.router';
import promptAction from '@ohos.promptAction';
import { TemplateEngine, TemplateItem } from '../model/TemplateEngine';
import { globalConfigManager } from '../entryability/EntryAbility';

@Entry
@Component
struct Index {
  @State templates: TemplateItem[] = [];
  @State hotkey: string = 'ctrl+shift+z';
  @State autostart: boolean = false;
  @State selectedIndex: number = -1;

  aboutToAppear(): void {
    this.loadConfig();
  }

  private async loadConfig(): Promise<void> {
    this.templates = await globalConfigManager.getTemplates();
    this.hotkey = globalConfigManager.getHotkey();
    this.autostart = globalConfigManager.getAutostart();
  }

  build() {
    Column() {
      // ===== 顶部标题栏 =====
      Row() {
        Text('TimestampTool')
          .fontSize(22)
          .fontWeight(FontWeight.Bold)
          .fontColor('#1A1A1A')
        Text('设置')
          .fontSize(16)
          .fontColor('#666666')
          .margin({ left: 8 })
      }
      .width('100%')
      .padding({ left: 24, top: 24, bottom: 16 })

      // ===== 模板管理区域 =====
      Column() {
        Text('模板管理')
          .fontSize(14)
          .fontWeight(FontWeight.Bold)
          .fontColor('#1A1A1A')
          .margin({ bottom: 8 })

        // 模板列表
        List() {
          ForEach(this.templates, (item: TemplateItem, index: number) => {
            ListItem() {
              Row() {
                Column() {
                  Text(item.name)
                    .fontSize(14)
                    .fontWeight(FontWeight.Medium)
                    .fontColor('#1A1A1A')
                  Text(TemplateEngine.previewTemplate(item.format))
                    .fontSize(11)
                    .fontColor('#666666')
                    .fontFamily('Consolas, monospace')
                    .margin({ top: 2 })
                }
                .alignItems(HorizontalAlign.Start)
                .layoutWeight(1)
              }
              .width('100%')
              .height(52)
              .padding({ left: 12, right: 12 })
              .borderRadius(8)
              .backgroundColor(this.selectedIndex === index ? '#E8F4FD' : Color.White)
              .onClick(() => {
                this.selectedIndex = index;
              })
            }
          })
        }
        .width('100%')
        .height(200)
        .borderRadius(8)
        .backgroundColor(Color.White)

        // 操作按钮
        Row() {
          Button('+ 添加')
            .fontSize(12)
            .height(32)
            .backgroundColor('#0078D4')
            .onClick(() => this.onAddTemplate())

          Button('删除')
            .fontSize(12)
            .height(32)
            .backgroundColor('#D13438')
            .margin({ left: 8 })
            .onClick(() => this.onDeleteTemplate())

          Button('重置默认')
            .fontSize(12)
            .height(32)
            .backgroundColor('#FF8C00')
            .margin({ left: 8 })
            .onClick(() => this.onResetTemplates())
        }
        .margin({ top: 8 })
      }
      .width('100%')
      .padding(16)
      .margin({ left: 16, right: 16, bottom: 12 })
      .borderRadius(12)
      .backgroundColor('#F5F5F5')

      // ===== 快捷键设置 =====
      Row() {
        Text('触发快捷键')
          .fontSize(14)
          .fontWeight(FontWeight.Bold)
          .fontColor('#1A1A1A')

        TextInput({ text: this.hotkey })
          .fontSize(13)
          .fontFamily('Consolas, monospace')
          .width(180)
          .height(36)
          .margin({ left: 12 })
          .borderRadius(6)
          .onChange((value: string) => {
            this.hotkey = value;
          })
      }
      .width('100%')
      .padding(16)
      .margin({ left: 16, right: 16, bottom: 12 })
      .borderRadius(12)
      .backgroundColor('#F5F5F5')

      // ===== 偏好设置 =====
      Row() {
        Text('开机自动启动')
          .fontSize(14)
          .fontWeight(FontWeight.Bold)
          .fontColor('#1A1A1A')

        Toggle({ type: ToggleType.Switch, isOn: this.autostart })
          .margin({ left: 12 })
          .onChange((isOn: boolean) => {
            this.autostart = isOn;
            globalConfigManager.setAutostart(isOn);
          })
      }
      .width('100%')
      .padding(16)
      .margin({ left: 16, right: 16, bottom: 12 })
      .borderRadius(12)
      .backgroundColor('#F5F5F5')

      // ===== 保存按钮 =====
      Button('保存设置')
        .width(120)
        .height(40)
        .fontSize(14)
        .backgroundColor('#0078D4')
        .margin({ top: 16 })
        .onClick(() => this.onSave())
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#FAFAFA')
  }

  private async onAddTemplate(): Promise<void> {
    // 简化实现：添加默认模板
    this.templates.push({ name: '新模板', format: '{YYYY}{MM}{DD}_##' });
    await globalConfigManager.setTemplates(this.templates);
    promptAction.showToast({ message: '已添加新模板，请编辑' });
  }

  private async onDeleteTemplate(): Promise<void> {
    if (this.selectedIndex < 0) {
      promptAction.showToast({ message: '请先选择要删除的模板' });
      return;
    }
    if (this.templates.length <= 1) {
      promptAction.showToast({ message: '至少保留一个模板' });
      return;
    }
    this.templates.splice(this.selectedIndex, 1);
    this.selectedIndex = -1;
    await globalConfigManager.setTemplates(this.templates);
  }

  private async onResetTemplates(): Promise<void> {
    await globalConfigManager.resetToDefault();
    await this.loadConfig();
    promptAction.showToast({ message: '已重置为默认配置' });
  }

  private async onSave(): Promise<void> {
    await globalConfigManager.setTemplates(this.templates);
    await globalConfigManager.setHotkey(this.hotkey);
    promptAction.showToast({ message: '设置已保存' });
  }
}
