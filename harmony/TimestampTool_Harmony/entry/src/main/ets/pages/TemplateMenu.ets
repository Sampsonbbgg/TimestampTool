/**
 * 模板选择浮窗菜单页面
 *
 * Fluent 双行卡片风格：
 * - 数字 Badge + 模板名（粗体）+ 预览（灰色等宽）
 * - 点击或按数字键选择 → 写入剪贴板 → 提示 Ctrl+V 粘贴
 * - ESC 关闭
 *
 * 此页面由 Emitter 事件触发弹出（HotkeyService 发出全局快捷键事件）。
 */

import emitter from '@ohos.events.emitter';
import { TemplateEngine, TemplateItem } from '../model/TemplateEngine';
import { ConfigManager } from '../model/ConfigManager';
import { ClipboardUtil } from '../utils/ClipboardUtil';
import { globalConfigManager } from '../entryability/EntryAbility';
import { HOTKEY_TRIGGER_EVENT_ID } from '../service/HotkeyService';

@Entry
@Component
struct TemplateMenu {
  @State templates: TemplateItem[] = [];
  @State previews: string[] = [];
  @State isVisible: boolean = false;

  aboutToAppear(): void {
    this.loadTemplates();
    // 监听全局快捷键事件
    emitter.on({ eventId: HOTKEY_TRIGGER_EVENT_ID }, () => {
      this.onHotkeyTriggered();
    });
  }

  aboutToDisappear(): void {
    emitter.off(HOTKEY_TRIGGER_EVENT_ID);
  }

  private async loadTemplates(): Promise<void> {
    this.templates = await globalConfigManager.getTemplates();
    this.previews = this.templates.map(t => TemplateEngine.previewTemplate(t.format));
  }

  private onHotkeyTriggered(): void {
    // 刷新预览（时间可能变了）
    this.previews = this.templates.map(t => TemplateEngine.previewTemplate(t.format));
    this.isVisible = true;
  }

  private async onSelectTemplate(index: number): Promise<void> {
    if (index < 0 || index >= this.templates.length) return;
    const template = this.templates[index];
    const formatted = TemplateEngine.formatTemplate(template.format);
    await ClipboardUtil.copyAndNotify(formatted);
    this.isVisible = false;
  }

  build() {
    Column() {
      if (this.isVisible) {
        Column() {
          // 标题
          Text('选择时间戳模板')
            .fontSize(16)
            .fontWeight(FontWeight.Bold)
            .fontColor('#1A1A1A')
            .margin({ top: 16, bottom: 12 })

          // 分隔线
          Divider()
            .strokeWidth(0.5)
            .color('#E0E0E0')
            .margin({ left: 16, right: 16, bottom: 8 })

          // 模板列表
          ForEach(this.templates, (item: TemplateItem, index: number) => {
            Row() {
              // 数字 Badge
              Text(`${index + 1}`)
                .fontSize(14)
                .fontWeight(FontWeight.Bold)
                .fontColor(Color.White)
                .textAlign(TextAlign.Center)
                .width(28)
                .height(28)
                .borderRadius(6)
                .backgroundColor('#0078D4')

              // 右侧两行文本
              Column() {
                Text(item.name)
                  .fontSize(14)
                  .fontWeight(FontWeight.Bold)
                  .fontColor('#1A1A1A')
                  .maxLines(1)
                  .textOverflow({ overflow: TextOverflow.Ellipsis })

                Text(this.previews[index] ?? '')
                  .fontSize(11)
                  .fontColor('#666666')
                  .fontFamily('Consolas, monospace')
                  .maxLines(1)
                  .textOverflow({ overflow: TextOverflow.Ellipsis })
                  .margin({ top: 2 })
              }
              .alignItems(HorizontalAlign.Start)
              .layoutWeight(1)
              .margin({ left: 12 })
            }
            .width('100%')
            .height(56)
            .padding({ left: 12, right: 12 })
            .borderRadius(8)
            .onClick(() => this.onSelectTemplate(index))
            .hoverEffect(HoverEffect.Highlight)
          })

          // 底部提示
          Text('按 1-9 选择  ·  ESC 关闭')
            .fontSize(10)
            .fontColor('#999999')
            .margin({ top: 12, bottom: 16 })
        }
        .width(380)
        .backgroundColor(Color.White)
        .borderRadius(12)
        .shadow({
          radius: 16,
          color: '#0000001A',
          offsetX: 0,
          offsetY: 4,
        })
      }
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
    .onKeyEvent((event) => {
      if (event.type === KeyType.Down && this.isVisible) {
        // ESC 关闭
        if (event.keyCode === 2070) {
          this.isVisible = false;
        }
        // 数字键 1-9 选择
        const num = event.keyCode - 2016; // keyCode 2017='1', 2018='2', ...
        if (num >= 1 && num <= 9 && num <= this.templates.length) {
          this.onSelectTemplate(num - 1);
        }
      }
    })
  }
}
