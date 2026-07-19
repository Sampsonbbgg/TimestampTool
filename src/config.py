"""TimestampTool 配置管理模块"""
import json
import os
import shutil
from pathlib import Path

from paths import user_config_path, legacy_config_paths


class ConfigManager:
    """JSON配置文件管理器"""
    
    # 默认配置
    # 注意：内容占位符使用 ## 而非 **
    # 原因：Windows 文件名不允许 * ? " < > | 反斜杠 正斜杠，用 ## 才能在
    # 文件重命名场景下完整粘贴、正确选中并被替换
    #
    # 默认快捷键：ctrl+shift+z（不与常见 IDE 快捷键 ctrl+shift+t 冲突）
    DEFAULT_CONFIG = {
        "version": "2.2",
        "settings": {
            "hotkey": "ctrl+shift+z",
            "theme": "light",
            "autostart": False
        },
        "templates": [
            {"name": "日期_内容_署名", "format": "{YYYY}_{MM}_{DD}_##_Sampson"},
            {"name": "内容_日期时间", "format": "##_{YYYY}{MM}{DD}_{hh}{mm}"},
            {"name": "日期时间_内容", "format": "{YYYY}{MM}{DD}{hh}{mm}_##"}
        ]
    }
    
    # 旧默认快捷键 → 新默认快捷键 的迁移映射
    # 只在检测到用户未自定义过（还是旧默认值）时才迁移
    _LEGACY_DEFAULT_HOTKEYS = {"ctrl+shift+t"}
    _CURRENT_DEFAULT_HOTKEY = "ctrl+shift+z"
    
    def __init__(self, config_path=None):
        """初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为:
                - 打包后: exe 同目录 / config.json（便携模式）
                - 开发环境: 项目根目录 / config / config.json
        """
        if config_path is None:
            config_path = user_config_path()
        self.config_path = Path(config_path)
        self.data = self.load()
    
    def load(self):
        """加载配置文件，失败时返回默认配置"""
        # 步骤 0: 从旧路径（exe 同目录）迁移到新路径（AppData），
        # 并清理 exe 同目录的老配置文件，避免污染用户视野
        self._migrate_from_legacy_location()

        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # 基本验证
                if 'templates' in data and 'settings' in data:
                    # 自动迁移旧占位符 ** → ##（一次性，静默）
                    data = self._migrate_placeholders(data)
                    # 自动迁移旧默认快捷键 ctrl+shift+t → ctrl+shift+z
                    # （只迁移"未自定义过"的用户；自定义过其他键的用户不动）
                    data = self._migrate_hotkey(data)
                    return data
            # 文件不存在，创建默认配置
            self._create_default()
            return self.DEFAULT_CONFIG.copy()
        except (json.JSONDecodeError, IOError, KeyError) as e:
            print(f"[配置加载失败] {e}，使用默认配置")
            return self.DEFAULT_CONFIG.copy()

    def _migrate_from_legacy_location(self):
        """把 exe 同目录的老 config 迁移到 AppData，并清理旧文件

        触发条件：仅在打包后 exe 环境生效
        迁移逻辑：
        - AppData 里还没配置 + 旧位置有配置 → 把旧配置搬到 AppData
        - 无论是否搬过，只要 AppData 里已有配置，就删除旧位置的 config 和 .bak
          （这一步是核心：从此用户在 exe 同目录再也看不到那两个文件）
        """
        legacy_paths = legacy_config_paths()
        if not legacy_paths:
            return  # 开发环境不迁移

        legacy_config = legacy_paths[0]  # config.json

        # 情形 A：AppData 里还没配置 + 旧位置有配置 → 搬过来
        if legacy_config.exists() and not self.config_path.exists():
            try:
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(legacy_config, self.config_path)
                print(f"[配置迁移] {legacy_config} → {self.config_path}")
            except Exception as e:
                print(f"[配置迁移失败，保留原位置] {e}")
                return  # 迁移失败就不删旧文件

        # 情形 B：AppData 已有配置 → 清理旧位置的所有污染文件
        if self.config_path.exists():
            for old_path in legacy_paths:
                if old_path.exists():
                    try:
                        old_path.unlink()
                        print(f"[配置清理] 已删除旧文件 {old_path}")
                    except Exception as e:
                        print(f"[清理失败] {old_path}: {e}")
    
    def _migrate_placeholders(self, data):
        """自动迁移旧内容占位符 ** → ##（一次性，静默）
        
        为什么迁移：Windows 文件名不允许 *，用户在文件重命名等场景使用
        含 ** 的模板会导致占位符被过滤、光标定位错乱。改为 ## 后完美工作。
        
        安全性：迁移前自动备份到 .bak；用户如果不希望迁移，可从备份恢复。
        """
        changed = False
        for tmpl in data.get('templates', []):
            fmt = tmpl.get('format', '')
            if '**' in fmt:
                tmpl['format'] = fmt.replace('**', '##')
                changed = True
        
        if changed:
            try:
                # 备份原文件
                self._backup()
                # 写回迁移后的配置
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print("[配置迁移] 内容占位符已从 ** 升级为 ##（原配置备份为 .bak）")
            except Exception as e:
                print(f"[配置迁移写回失败] {e}")
        
        return data
    
    def _migrate_hotkey(self, data):
        """自动迁移旧默认快捷键 → 新默认快捷键
        
        策略：只在检测到用户当前 hotkey 属于历史默认值时迁移，
        避免覆盖用户自定义过的快捷键。
        
        例：ctrl+shift+t 是旧默认，如果用户从没改过（还是这个值），
        自动升级为新默认 ctrl+shift+z。
        """
        settings = data.get('settings', {})
        current = str(settings.get('hotkey', '')).strip().lower()
        
        if current in self._LEGACY_DEFAULT_HOTKEYS:
            new_hotkey = self._CURRENT_DEFAULT_HOTKEY
            data.setdefault('settings', {})['hotkey'] = new_hotkey
            try:
                self._backup()
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(
                    f"[配置迁移] 默认快捷键已从 {current} 升级为 {new_hotkey}"
                    "（原配置备份为 .bak）"
                )
            except Exception as e:
                print(f"[配置迁移写回失败] {e}")
        
        return data
    
    def save(self, data=None):
        """保存配置，保存前自动备份"""
        if data is not None:
            self.data = data
        
        # 备份现有配置
        self._backup()
        
        # 确保目录存在
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入配置
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    def _backup(self):
        """备份当前配置文件"""
        if self.config_path.exists():
            backup_path = self.config_path.with_suffix('.json.bak')
            shutil.copy2(self.config_path, backup_path)
    
    def _create_default(self):
        """创建默认配置文件"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
    
    @property
    def templates(self):
        """获取模板列表"""
        return self.data.get('templates', self.DEFAULT_CONFIG['templates'])
    
    @templates.setter
    def templates(self, value):
        """设置模板列表"""
        self.data['templates'] = value
    
    @property
    def hotkey(self):
        """获取快捷键设置"""
        return self.data.get('settings', {}).get('hotkey', self._CURRENT_DEFAULT_HOTKEY)
    
    @hotkey.setter
    def hotkey(self, value):
        """设置快捷键"""
        if 'settings' not in self.data:
            self.data['settings'] = {}
        self.data['settings']['hotkey'] = value
    
    @property
    def theme(self):
        """获取主题设置"""
        return self.data.get('settings', {}).get('theme', 'light')
    
    @property
    def autostart(self) -> bool:
        """获取开机自启偏好（用户上次设置的值；实际生效状态请查 autostart.is_enabled()）"""
        return bool(self.data.get('settings', {}).get('autostart', False))
    
    @autostart.setter
    def autostart(self, value: bool):
        """设置开机自启偏好（仅记录，实际生效需调用 autostart.sync()）"""
        if 'settings' not in self.data:
            self.data['settings'] = {}
        self.data['settings']['autostart'] = bool(value)
    
    def reload(self):
        """重新加载配置"""
        self.data = self.load()
    
    def reset_to_default(self):
        """重置为默认配置"""
        self.data = self.DEFAULT_CONFIG.copy()
        self.save()
