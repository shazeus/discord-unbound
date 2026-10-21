# Uyumluluk incelemesi / Compatibility audit

21 Ekim / October 2026. Windows Discord Stable **1.0.9264**.

## Türkçe

Bu incelemede kurulu masaüstü istemcisinin gönderilmiş kodu statik olarak incelendi. Satın alma yapılmadı; hesap önbelleği, oturum belirteci, çerez ve ödeme bilgileri okunmadı.

- İncelenen paket: `discord_desktop_core-1/discord_desktop_core/core.asar`.
- SHA-256: `922c22e53eceb3a62fdfa51240ebbbb55e8e75cbc03caa6b711f6193448fa48e`.
- Sınır: ASAR envanteri ile `bundle.js`, `mainScreenPreload.js`, `frameViewPreload.js` içindeki ilgili statik çağrılar. Uzaktan indirilen Discord arayüzü ve ödeme sağlayıcılarının kodu bu kapsamın dışındadır.

**Dış tarayıcı:** `OPEN_EXTERNAL_URL` IPC işleyicisi ve dış pencere bağlantıları uygun adresleri Electron `shell.openExternal` çağrısına iletir. İşletim sistemi tarayıcısı Discord Unbound'un uygulama içi PAC ayarını kullanmaz. Dış tarayıcıya geçen ödeme, kimlik doğrulama ve 3D Secure bağlantılarının çözüldüğü iddia edilmez. Bu davranış değiştirilmedi.

**Doğrulanan hata:** Önceki PAC, HTTP Discord adreslerini de yerel proxy'ye gönderiyordu; proxy bu isteklere 404 veriyordu. 0.1.1 sürümü, izinli hedeflere giden GET/HEAD bağlantılarını aynı yol ve sorgu ile HTTPS'ye 307 yönlendirmesi yapar. Gövdeli işlem istekleri tekrar gönderilmez. Ödeme içeriği ve sonuçları değiştirilmez.

**Alan adı kapsamı:** Resmi `discord.gift` ve `dis.gd` bağlantıları için tam alan adı eşleşmesi eklendi. Yeni alanlar güncelleme manifestinin güvenilir kaynak listesine eklenmedi. Stripe, PayPal, diğer ödeme sağlayıcıları ve kimlik doğrulama siteleri normal doğrudan yolda kalır.

**Sınırlar:** İncelenen çekirdek dosyada `setProxy`, `fromPartition`, `checkout`, `payment`, `stripe` ve `paypal` literal eşleşmesi bulunmadı. Bu, uzaktan yüklenen veya dinamik kodda ilgili özelliklerin olmadığı anlamına gelmez. Çerçeve adresleri dinamik sağlanır; statik analiz bunların ödeme sağlayıcısını belirlemez.

Bir Nitro sayfasının veya genel ödeme SDK'sının açılması gerçek ödemenin tamamlandığını kanıtlamaz. Satın alma, abonelik, hediye kullanımı ve 3D Secure işlemleri denenmedi. Banka, bölge ve sağlayıcı kısıtlamaları ağ erişiminden bağımsız olabilir.

## English

This audit statically inspected shipped code from the installed desktop application without making purchases. Account caches, session tokens, cookies and payment details were not read.

- Package: `discord_desktop_core-1/discord_desktop_core/core.asar`.
- SHA-256: `922c22e53eceb3a62fdfa51240ebbbb55e8e75cbc03caa6b711f6193448fa48e`.
- Boundary: ASAR file inventory and external-link, window-opening, proxy and session-configuration call sites in `bundle.js`. Remotely downloaded Discord interface code and third-party payment-provider code are outside this audit.

**Confirmed behavior:** The desktop `OPEN_EXTERNAL_URL` IPC handler and external window-link handlers pass eligible URLs to Electron `shell.openExternal`. These links may open in the operating system browser. Discord Unbound's process-local PAC does not configure that browser. It therefore does not claim to fix connectivity in purchase, authentication or 3-D Secure flows that move to an external browser.

**Payment coverage:** No purchase, subscription, gift purchase or payment verification was attempted. Loading the in-app Nitro screen would not prove that a real payment succeeds. Bank, region, payment-method and provider restrictions may be independent of network access.

**Proxy boundary:** Third-party payment providers are outside the Discord domain scope and retain their normal direct connection. Payment-page URLs, credentials and payment content are not rewritten. The local HTTP handling fix is intended only to redirect GET/HEAD requests for approved Discord domains to HTTPS; transaction bodies are not replayed.

**Static limitations:** No literal matches for `setProxy`, `fromPartition`, `checkout`, `payment`, `stripe` or `paypal` were found in the inspected `bundle.js`. This does not establish absence in remotely loaded interface code or dynamic/native code. Live purchase success remains unverified.

## Evidence / Kanıt

REA selected-source analysis: `ev_2b249cd8682dab3012c21c9ea0ec7519273844a22c71c5b68604791d3b46f0f2` (`bundle.js`, `mainScreenPreload.js`, `frameViewPreload.js`). Separate inventory/package receipt: `ev_ff10f736b702541b4806e2fe2bbedeafddb58d86d451fde7563c9d47c4d09e82`. Static graph coverage is partial; these references do not establish runtime checkout execution.

Exact static call-site anchors (zero-based decoded JavaScript character offsets): `bundle.js` offset 161735 (`OPEN_EXTERNAL_URL` handler), 83139 (frame-view window-open handler), 270734 (external-opening helper). `frameViewPreload.js` creates its iframe from `options.src` near offset 4338. The actual frame origin is supplied dynamically; no payment-provider origin is established by that statement.
