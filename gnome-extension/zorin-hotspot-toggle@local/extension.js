import GObject from 'gi://GObject';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import St from 'gi://St';
import Clutter from 'gi://Clutter';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as QuickSettings from 'resource:///org/gnome/shell/ui/quickSettings.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

const HOTSPOTCTL  = '/usr/local/bin/zorin-hotspotctl';
const GTK_APP     = '/usr/local/bin/zorin-hotspot-switcher';
const CONFIG_DIR  = GLib.get_home_dir() + '/.config/zorin-hotspot-switcher';
const CONFIG_FILE = CONFIG_DIR + '/config.conf';
const SYS_CONFIG  = '/etc/zorin-hotspot-switcher.conf';
const POLL_S      = 5;

// ── Config yardımcıları ───────────────────────────────────────────────────────

function readConfig() {
    const defaults = {
        HOTSPOT_SSID:           'ZorinHotspot',
        HOTSPOT_PASSWORD:       '12345678',
        HOTSPOT_BACKEND:        'create_ap',
        PREFER_24GHZ_ON_START:  'yes',
        RETURN_TO_5GHZ_ON_STOP: 'yes',
        PREFERRED_24GHZ_BSSID:  '',
        PREFERRED_5GHZ_BSSID:   '',
    };
    const cfg = {...defaults};
    for (const path of [SYS_CONFIG, CONFIG_FILE]) {
        try {
            const [ok, bytes] = GLib.file_get_contents(path);
            if (!ok) continue;
            for (let line of new TextDecoder().decode(bytes).split('\n')) {
                line = line.trim();
                if (!line || line.startsWith('#') || !line.includes('=')) continue;
                const idx = line.indexOf('=');
                const key = line.slice(0, idx).trim();
                const val = line.slice(idx + 1).trim().replace(/^["']|["']$/g, '');
                if (key in cfg) cfg[key] = val;
            }
        } catch (_) {}
    }
    return cfg;
}

function writeConfig(cfg) {
    const lines = ['# Zorin Hotspot Switcher — kullanıcı ayarları\n'];
    for (const [k, v] of Object.entries(cfg))
        lines.push(`${k}="${v}"\n`);
    try {
        GLib.mkdir_with_parents(CONFIG_DIR, parseInt('0755', 8));
        const file = Gio.File.new_for_path(CONFIG_FILE);
        const stream = file.replace(null, false, Gio.FileCreateFlags.REPLACE_DESTINATION, null);
        stream.write_all(new TextEncoder().encode(lines.join('')), null);
        stream.close(null);
        return true;
    } catch (e) {
        logError(e, 'ZorinHotspot: config yazılamadı');
        return false;
    }
}

// ── Girdi satırı: etiket + St.Entry — taşmayı önlemek için sabit em genişliği ─

function makeEntryRow(labelText, password = false) {
    // PopupBaseMenuItem zaten St.BoxLayout'tur; doğrudan çocuk ekliyoruz.
    const item = new PopupMenu.PopupBaseMenuItem({
        activate: false,
        can_focus: false,
        style_class: 'zorin-hs-row',
    });

    const lbl = new St.Label({
        text: labelText,
        y_align: Clutter.ActorAlign.CENTER,
        style_class: 'zorin-hs-label',
    });

    const entry = new St.Entry({
        can_focus: true,
        style_class: 'search-entry zorin-hs-entry',
    });

    if (password) {
        entry.clutter_text.set_password_char('•');
        const eye = new St.Icon({
            icon_name: 'view-reveal-symbolic',
            icon_size: 16,
            reactive: true,
            can_focus: false,
            style: 'padding: 0 4px;',
        });
        let visible = false;
        entry.connect('secondary-icon-clicked', () => {
            visible = !visible;
            entry.clutter_text.set_password_char(visible ? '' : '•');
            eye.icon_name = visible ? 'view-conceal-symbolic' : 'view-reveal-symbolic';
        });
        entry.set_secondary_icon(eye);
    }

    item.add_child(lbl);
    item.add_child(entry);
    return {item, entry};
}

// ── Toggle bileşeni ───────────────────────────────────────────────────────────

const HotspotToggle = GObject.registerClass(
class HotspotToggle extends QuickSettings.QuickMenuToggle {
    _init() {
        super._init({
            title: 'Hotspot',
            iconName: 'network-wireless-hotspot-symbolic',
            toggleMode: true,
            // GNOME 45+ yapıcı parametresi — setHeader() yerine daha güvenilir
            menuEnabled: true,
        });

        // Async işlemleri iptal etmek için Cancellable
        this._cancellable    = new Gio.Cancellable();
        this._syncing        = false;
        this._busy           = false;
        this._statusPending  = false;

        this._buildMenu();

        this.connect('notify::checked', () => {
            if (this._syncing) return;
            this._onUserToggle();
        });

        this._pollTimer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, POLL_S, () => {
            if (!this._busy) this._syncStatus();
            return GLib.SOURCE_CONTINUE;
        });

        this._syncStatus();
    }

    _buildMenu() {
        // SSID ve Şifre girişleri
        const {item: ssidItem, entry: ssidEntry} = makeEntryRow('SSID');
        const {item: passItem, entry: passEntry} = makeEntryRow('Şifre', true);
        this._ssidEntry = ssidEntry;
        this._passEntry = passEntry;

        this.menu.addMenuItem(ssidItem);
        this.menu.addMenuItem(passItem);
        this.menu.addAction('Kaydet', () => this._onSave());
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this.menu.addAction('Tüm Ayarlar...', () => {
            this.menu.close();
            try { GLib.spawn_command_line_async(GTK_APP); } catch (e) {
                logError(e, 'ZorinHotspot: GTK uygulama başlatılamadı');
            }
        });

        this._loadFields();

        // Menü her açıldığında mevcut config'i yükle
        this.menu.connect('open-state-changed', (_, open) => {
            if (open) this._loadFields();
        });
    }

    _loadFields() {
        const cfg = readConfig();
        this._ssidEntry.set_text(cfg['HOTSPOT_SSID']);
        this._passEntry.set_text(cfg['HOTSPOT_PASSWORD']);
    }

    _onSave() {
        const ssid = this._ssidEntry.get_text().trim();
        const pass = this._passEntry.get_text().trim();
        if (!ssid) {
            Main.notify('Zorin Hotspot', 'SSID boş olamaz.');
            return;
        }
        if (pass.length < 8) {
            Main.notify('Zorin Hotspot', 'Şifre en az 8 karakter olmalı.');
            return;
        }
        const cfg = readConfig();
        cfg['HOTSPOT_SSID']     = ssid;
        cfg['HOTSPOT_PASSWORD'] = pass;
        if (writeConfig(cfg)) {
            log(`ZorinHotspot: config kaydedildi (SSID=${ssid})`);
            this.menu.close();
        } else {
            Main.notify('Zorin Hotspot', 'Ayarlar kaydedilemedi.');
        }
    }

    // ── Durum sorgulama ───────────────────────────────────────────────────────

    _syncStatus() {
        if (this._statusPending) return;
        this._statusPending = true;

        let proc;
        try {
            proc = Gio.Subprocess.new(
                [HOTSPOTCTL, 'status'],
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE
            );
        } catch (e) {
            logError(e, 'ZorinHotspot: status başlatılamadı');
            this._statusPending = false;
            return;
        }

        // _cancellable ile iptal edilebilir: disable() çağrısında bekleyen callback temizlenir
        proc.communicate_utf8_async(null, this._cancellable, (_proc, result) => {
            this._statusPending = false;
            let out = '';
            try {
                const [, stdout] = _proc.communicate_utf8_finish(result);
                out = (stdout ?? '').trim();
            } catch (e) {
                // CANCELLED hatası beklenen; diğerlerini logla
                if (!e.matches(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
                    logError(e, 'ZorinHotspot: status okunamadı');
                return;
            }

            log(`ZorinHotspot: durum="${out}"`);
            const active = /running|started|active/.test(out);
            this._syncing = true;
            this.checked  = active;
            this.subtitle = active
                ? `Açık — ${readConfig()['HOTSPOT_SSID'] ?? 'Hotspot'}`
                : 'Kapalı';
            this._syncing = false;
        });
    }

    // ── Komut çalıştırma ──────────────────────────────────────────────────────

    _runCommand(args, onDone) {
        let proc;
        try {
            proc = Gio.Subprocess.new(
                args,
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE
            );
        } catch (e) {
            logError(e, `ZorinHotspot: '${args[1]}' başlatılamadı`);
            if (onDone) onDone(false);
            return;
        }

        proc.communicate_utf8_async(null, this._cancellable, (_proc, result) => {
            let ok = false;
            try {
                const [, stdout, stderr] = _proc.communicate_utf8_finish(result);
                const exitCode = _proc.get_exit_status();
                ok = (exitCode === 0);
                const details = [(stdout ?? '').trim().replace(/\n/g, ' ↵ '),
                                 (stderr ?? '').trim().replace(/\n/g, ' ↵ ')]
                    .filter(s => s).join(' | ');
                log(`ZorinHotspot: ${args[1]} → çıkış=${exitCode} "${details}"`);
                if (!ok)
                    logError(new Error(`exit ${exitCode}: ${details}`), `ZorinHotspot: ${args[1]} başarısız`);
            } catch (e) {
                if (!e.matches(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED))
                    logError(e, `ZorinHotspot: ${args[1]} iletişim hatası`);
                if (onDone) onDone(false);
                return;
            }
            if (onDone) onDone(ok);
        });
    }

    _onUserToggle() {
        this._busy = true;
        if (this.checked) {
            this.subtitle = 'Açılıyor...';
            this._runCommand(['sudo', HOTSPOTCTL, 'start'], () => {
                this._busy = false;
                this._syncStatus();
            });
        } else {
            this.subtitle = 'Kapatılıyor...';
            this._runCommand(['sudo', HOTSPOTCTL, 'stop'], () => {
                this._busy = false;
                this._syncStatus();
            });
        }
    }

    destroy() {
        // Tüm bekleyen async işlemleri iptal et — "this._indicator is null" hatasını önler
        this._cancellable.cancel();

        if (this._pollTimer) {
            GLib.Source.remove(this._pollTimer);
            this._pollTimer = null;
        }
        super.destroy();
    }
});

// ── Extension ─────────────────────────────────────────────────────────────────

export default class ZorinHotspotToggleExtension extends Extension {
    enable() {
        this._indicator = new QuickSettings.SystemIndicator();
        this._toggle    = new HotspotToggle();
        this._indicator.quickSettingsItems.push(this._toggle);
        Main.panel.statusArea.quickSettings.addExternalIndicator(this._indicator);
        log('ZorinHotspot: extension etkinleştirildi');
    }

    disable() {
        // Önce toggle'ı yok et (timer ve Cancellable iptal olur)
        this._toggle?.destroy();
        this._toggle = null;
        // Sonra indicator'ı temizle
        this._indicator?.destroy();
        this._indicator = null;
        log('ZorinHotspot: extension devre dışı bırakıldı');
    }
}
