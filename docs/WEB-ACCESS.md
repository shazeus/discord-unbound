# Web erişimi / Browser access

## Türkçe

0.2.0 sürümü, Discord masaüstü sürecinden bağımsız çalışan yerel bir HTTPS CONNECT yardımcısı içerir. Yalnızca geçerli kullanıcının varsayılan LAN WinINet otomatik proxy/PAC ayarı değiştirilir. Değişiklik isteğe bağlıdır; GUI'de veya `--web-start` ile açılır.

`InternetQueryOptionW` ile flags, proxy adresi, bypass listesi ve PAC adresi alınır. Snapshot, değişiklikten önce `%LOCALAPPDATA%/DiscordUnbound/web-state.json` içine atomik olarak yazılır. Yardımcı döngü adresinde dinlemeye başladıktan ve bağımsız kurtarma gözeticisi hazır olduktan sonra PAC etkinleştirilir. `InternetSetOptionW` ayar değişikliği ve yenileme bildirimlerini gönderir. Yönetici yetkisi, makine WinHTTP ayarı veya sertifika kurulumu gerekmez.

PAC, Discord alanları dışında eski PAC işlevini veya manual/doğrudan seçimini çalıştırır. Genel ödeme ve kimlik doğrulama siteleri kapsam dışında kalır. Eski PAC başlangıçta alınmış bir kopyadır; uzaktaki politika değişirse yardımcı yeniden başlatılmalıdır. WPAD-only kurulumlar güvenli birleştirme desteklenmediği için reddedilir. Erişilmeyen eski loopback PAC ayarı yedeklenerek mevcut manual/doğrudan fallback korunur.

Normal kapanış ve işçi sürecinin zorla sonlandırılması test edildi. Geri dönüş yalnızca hâlâ bu oturumun PAC adresine ait ayarları geri alır; başka uygulamanın yeni PAC adresi veya sonradan değişmiş manual proxy alanları korunur. Gözeticinin de işletim sistemi tarafından sonlandırılması veya kapanış anında başka bir politika uygulaması gibi koşullar için mutlak garanti yoktur. Sonraki başlatma, kalmış oturumu kendi PAC sahipliği üzerinden kurtarmayı da dener.

**Doğrulama:** Windows PAC çözümleyicisi Discord için loopback yolunu ve HTTP 200 yanıtını, Cloudflare/Stripe için DIRECT ve HTTP 200 yanıtını verdi. Sertifika doğrulaması açıktı. Mevcut normal Brave sekmesi önce bağlantı sıfırlama hatası gösterirken yardımcı açıldıktan sonra yenilemeyle Discord ana sayfasını açtı. Ödeme veya hesap işlemi yapılmadı.

## English

Version 0.2.0 adds a local HTTPS CONNECT helper independent of the Discord desktop process. It changes only the current user's default LAN WinINet automatic proxy/PAC setting, on explicit GUI or `--web-start` activation.

Flags, server, bypass and PAC URL are queried with `InternetQueryOptionW`. A snapshot is atomically journaled before mutation. The helper starts listening and the independent recovery guard acknowledges readiness before settings are changed. `InternetSetOptionW` broadcasts settings-change and refresh notifications. No administrator rights, machine WinHTTP changes or certificates are required.

Non-Discord traffic executes the previous PAC function or manual/direct selection. Payment and identity-provider sites remain outside the Discord routing scope. Existing PAC code is a startup snapshot; restart the helper after a remote policy update. WPAD-only setups are refused rather than silently replaced. An unreachable previous loopback PAC is backed up while its manual/direct fallback is retained.

Both normal shutdown and forced worker termination were tested. Restoration is ownership-aware and preserves a new PAC address or manual proxy fields changed by another application. Recovery is not an absolute guarantee if the guard is also terminated or another policy manager interferes. Startup also attempts ownership-checked recovery of a stale session.

**Verification:** Windows PAC resolved Discord to the loopback helper with HTTP 200, and Cloudflare/Stripe to DIRECT with HTTP 200. Certificate validation stayed enabled. Reloading the existing normal Brave tab changed its connection-reset error into the rendered Discord homepage. No payment or account action was performed.

Implementation reference: [Microsoft — setting and retrieving Internet options](https://learn.microsoft.com/en-us/windows/win32/wininet/setting-and-retrieving-internet-options).
