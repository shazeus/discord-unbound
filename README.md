<p align="center">
  <img width="1774" height="887" alt="ChatGPT Görseli 26 Eki 2026 13_45_10" src="https://github.com/user-attachments/assets/3664d1e6-602d-4220-917e-fa33f4f5149e" />
</p>

<p align="center"><strong>Türkçe</strong> · <a href="README.en.md">English</a></p>

# Discord Unbound

> Ben ezelden beridir hür yaşadım, hür yaşarım.  
> Hangi çılgın bana zincir vuracakmış? Şaşarım!  
> Kükremiş sel gibiyim; bendimi çiğner, aşarım;  
> Yırtarım dağları, enginlere sığmam, taşarım.
>
> — Mehmet Âkif Ersoy, *İstiklal Marşı*

## Neden bu dizeler?

Discord Unbound, Türkiye'deki insanların da herkes gibi özgürce iletişim kurabilmesi gerektiği düşüncesinden doğdu. İstiklal Marşı'nın bu kıtası burada bir süs olarak değil, projenin çıkışındaki özgürlük ve bağımsızlık anlayışını ifade etmek için yer alıyor. Zincire vurulamamak ve önüne konulan bendi aşmak, iletişimin teknik engellerle sınırlandırılmaması gerektiğine duyduğum inancın karşılığı.

**Unbound**, “bağlarından kurtulmuş, sınırlandırılmamış” anlamını taşıyor. Projenin amacı, bu düşünceyi günlük kullanımda somut bir araca dönüştürmek: bildiğin Discord uygulamasını, bildiğin arayüzüyle kullanabilmek.

## Ne işe yarar?

Discord Unbound, Windows'ta kurulu **orijinal Discord masaüstü istemcisine** geri alınabilir bir bağlantı uyarlaması ekleyen açık kaynaklı bir başlatıcı ve yama aracıdır. İncelenen bağlantıda Discord'un TLS trafiğine uygulanan filtrelemeyi, Discord sürecinin içinde çalışan yerel bir aktarım katmanıyla aşmayı hedefler.

Discord'un arayüzünü yeniden yazmaz; hesap, sunucu ve mesajlaşma özelliklerini orijinal istemci sağlar. Bu depo Discord'un kapalı kaynak kodunu, kurulum dosyalarını veya yerel modüllerini dağıtmaz. Kullanıcının kendi resmi kurulumuna küçük bir başlangıç sarmalayıcısı ekler.

### Temel özellikler

- **Discord'a özel bağlantı yolu:** Discord alan adları Electron oturumunda yerel modüle yönlendirilir; diğer alan adları doğrudan bağlantıda kalır.
- **Uzak VPN sunucusu gerektirmez:** bilgisayarın genel trafiğini bir tünele almaz. Masaüstü bağlantı yaması DNS/proxy/rota ayarlarını değiştirmez; **Yamala ve aç** kullanıcıya ait başlangıç kaydını yönetir; isteğe bağlı web modu yalnızca mevcut kullanıcının otomatik proxy/PAC ayarını geçici olarak düzenler ve geri yükler.
- **TLS kayıt bölümleme:** ilk `ClientHello` mesajının baytlarını koruyarak TLS kayıtlarını küçük parçalara böler. Mesajlaşma bağlantısında TLS çözülmez ve sertifika doğrulaması kapatılmaz.
- **Yerel güncelleyici uyarlaması:** resmi manifest ve paket isteklerini aynı bağlantı katmanından geçirir; paket içeriğini ve manifestteki SHA-256 alanlarını korur.
- **Ses bağlantısı desteği:** `discord.media` üzerindeki ses kontrol bağlantısının verdiği TLS portunu korur; 2053 portu ayrıca test edilmiştir. UDP ses paketleri doğrudan gider.
- **Geri alınabilir yama:** orijinal arşiv yedeği, dosya özeti denetimi, işlem kilidi ve orijinale dönüş içerir.
- **Kalıcı sürüm gözlemcisi:** Windows oturum açılışında geri başlar; yalnızca etkinleştirdiğin kanalların uygun, kullanılmayan yeni sürümlerini yamalar.

## İndir ve çalıştır

**[En güncel sürümü indir](https://github.com/shazeus/discord-unbound/releases/latest)**

1. Sürüm sayfasındaki `DiscordUnbound-windows-x64.zip` paketini indirip bir klasöre çıkar.
2. Discord'u sistem tepsisindeki simgesinden **tamamen kapat**.
3. `DiscordUnbound.exe` dosyasını aç.
4. Listeden kurulumunu seç ve **Yamala ve aç** düğmesine bas.

Hazır pakette Python veya Node.js kurulu olması gerekmez. **Yamala ve aç**, başlatıcının doğrulanmış kopyasını `%LOCALAPPDATA%\DiscordUnbound\launcher` altında saklar ve kullanıcıya ait `DiscordUnbound` başlangıç kaydını ekler. ZIP klasörü taşınsa veya silinse de gözlemci sonraki Windows oturumunda başlar. Yönetici izni, servis veya zamanlanmış görev gerekmez.

Discord zaten Windows başlangıcında açılacak şekilde kayıtlıysa o kayıt yedeklenip önce en yeni sürümü hazırlayan başlatma yoluna yönlendirilir. Otomatik Discord açılışı kapalıysa bu tercih açılmaz; yalnızca gözlemci başlar. El ile açarken **Discord Unbound → Yamala ve aç** kullan: sıradan Discord kısayolu hazırlığı atlayabilir. **Yalnızca yamala** kalıcı başlangıç kaydı oluşturmaz.

**Başlangıç kaydını ve kalıcı izlemeyi kapat** düğmesi mevcut yamayı değiştirmeden kaydı kaldırır ve gözlemciyi durdurur. Başka uygulamaların sonradan değiştirdiği başlangıç değerlerinin üzerine yazılmaz. Discord'u tamamen kapatıp **Orijinale dön** seçeneğini kullanmak hem arşivi geri yükler hem o kanalın kalıcı kaydını kaldırır.

## Normal tarayıcıda Discord sitesi

**Web erişimini aç** düğmesine bas. Ardından Brave, Chrome, Edge veya Windows'un proxy ayarlarını kullanan tarayıcında normal `https://discord.com` adresini açabilirsin. Eklenti, ayrı tarayıcı profili veya uzak sunucu gerekmez. **Discord sitesini aç** düğmesi aynı özelliği açıp varsayılan tarayıcıyı başlatır. Web modu Discord masaüstü uygulaması kurulu olmadan da çalışabilir.

- Yerel yardımcı yalnızca `127.0.0.1` üzerinde çalışır; yalnızca Discord adresleri ona yönlendirilir.
- Diğer siteler önceki doğrudan/manual proxy/PAC yolunu korur. Erişilebilir eski PAC betiği başlangıçta alınıp yeni kuralla birleştirilir.
- **Web erişimini kapat** veya pencereyi kapatmak önceki ayarları geri yükler. Komut satırından açılan yardımcı, açıkça kapatılana kadar arka planda kalır.
- Bağımsız kurtarma gözeticisi, yardımcı beklenmedik biçimde kapanırsa ayarları geri yükler. Başka bir uygulamanın sonradan değiştirdiği PAC adresinin üzerine yazılmaz.
- Web modu oturum açılışında kendiliğinden başlamaz. Masaüstü gözlemcisi kullanıcı başlangıç kaydı kullanır; servis/görev eklenmez; WinHTTP makine ayarı, sistem DNS'i, rota, güvenlik duvarı ve sertifika deposu değiştirilmez.

Bu sürüm geçerli kullanıcının varsayılan LAN internet ayarını kullanır. Tarayıcı kendi proxy ayarını/eklentisini kullanıyorsa Windows ayarını izlemeyebilir. Yalnızca WPAD otomatik keşfine dayanan mevcut bir politika güvenle birleştirilemediğinde etkinleştirme reddedilir. Eski PAC erişilemeyen bir yerel adrese işaret ediyorsa adres yedeklenir, etkin oturumda eski manual/doğrudan fallback kullanılır ve kapatınca özgün ayar geri gelir. Eski PAC betiğinin sunucuda değişmesi durumunda yardımcı yeniden başlatılmalıdır.

Web modunda TLS sertifika doğrulaması açık kalır. Ödeme sağlayıcıları doğrudan gider; gerçek ödeme veya 3D Secure işlemi test edilmiş değildir.

## Kaldırma

Discord Unbound taşınabilir bir uygulamadır; Denetim Masası veya **Ayarlar → Uygulamalar** listesine kurulum kaydı eklemez. Tamamen kaldırmak için:

1. Discord'u sistem tepsisindeki simgesinden **tamamen kapat**.
2. Discord Unbound'u aç, yamaladığın kurulumu seç ve **Orijinale dön** düğmesine bas. Birden fazla kurulumu yamaladıysan her biri için tekrarla. Yalnızca web modunu kullandıysan bu adımı atlayabilirsin.
3. **Başlangıç kaydını ve kalıcı izlemeyi kapat** düğmesiyle kalan masaüstü kaydını kaldır; yama dosyası silinmiş olsa da kullanılabilir. Ardından **Web erişimini kapat** düğmesine bas ve kapandığını doğrula. Bu işlem web yardımcısını durdurur ve önceki Windows proxy/PAC ayarlarını geri yükler.
4. Discord Unbound penceresini kapat; ZIP'ten çıkardığın uygulama klasörünü ve oluşturduğun kısayolları sil.
5. Gözlemci durduktan ve önceki proxy ayarı geri geldikten sonra `Win + R` ile `%LOCALAPPDATA%\DiscordUnbound` klasörünü açıp kalıcı başlatıcı kopyaları dahil kalan dosyaları silebilirsin.

**Önce geri yükle, sonra sil:** orijinale dönüş veya web erişimini kapatma başarısız olursa uygulamayı, yedekleri ve durum kayıtlarını silmeden önce hatayı çöz. Özellikle `web-state.json` önceki proxy ayarlarını içerir; ayarlar geri yüklenmeden silinmemelidir. Bu işlemler Discord hesabını veya orijinal Discord uygulamasını kaldırmaz.

## Mimari

```text
DiscordUnbound.exe
  ├─ Kurulum keşfi ve çalışan işlem denetimi
  ├─ ASAR doğrulama → orijinal yedek → başlangıç sarmalayıcısı
  └─ Resmi Discord başlatma akışı + sürüm gözlemcisi

Discord ana süreci
  ├─ Electron oturumuna özel PAC kuralı
  │    └─ 127.0.0.1 → TLS kayıt bölümleme → Discord
  └─ Yerel güncelleyici kurucu uyarlaması
       └─ Oturum anahtarlı yerel uç nokta → doğrulanmış HTTPS → resmi depo/CDN
```

### Başlangıç ve arşiv yaması

Araç, `resources/app.asar` içindeki `package.json` dosyasının `main` alanını çözümler. Arşiv sınırları, dosya yolları, başlangıç türü ve komşu Discord çalıştırılabilir dosyasındaki Electron fuse durumu doğrulanır. Gömülü ASAR bütünlük zorlaması etkinse veya durum okunamıyorsa işlem durur; çalıştırılabilir dosyanın fuse değerleri değiştirilmez.

Başlangıç alanı eklenen küçük bir CommonJS dosyasına yönlendirilir. Bağlantı modülü hazır olduğunda orijinal başlangıç dosyası çalıştırılır. Eklenen/değişen arşiv girdilerinin SHA-256 bütünlük bilgileri güncellenir. Orijinal ASAR'ın tam baytları ayrı bir yedekte saklanır.

### Bağlantı katmanı

Yerel dinleyici yalnızca `127.0.0.1` üzerinde açılır. PAC kuralı `discord.com`, `discord.gg`, `discordapp.com`, `discordapp.net` ve `discord.media` alanlarını ve alt alanlarını kapsar. Çözümlenen özel/yerel IP adresleri reddedilir. Genel Discord hedeflerinde TLS portu 443 ile sınırlıdır; ses sunucuları için `discord.media` alanında geçerli TCP portu korunur.

Alan adları önce Google DNS-over-HTTPS ile çözülür. Başarısızlık durumunda süre sınırıyla sistem DNS'ine dönülür; hangi yolun kullanıldığı durum kaydına yazılır. Google DNS, bu sorgulardaki alan adlarını ve kaynak IP adresini görebilir.

### Güncelleme akışı

Discord'un yerel Rust güncelleyicisi Electron oturumunun proxy ayarını kullanmadığından ayrı bir uyarlama gerekir. Yalnızca çalıştırılabilir dosyanın yanındaki `updater.node` modülünün `Updater` kurucusu sarılır. Depo adresi, rastgele bir oturum anahtarı içeren yerel uç noktaya yönlendirilir.

Modül resmi manifesti sertifikası doğrulanmış HTTPS ile alır. Manifestteki paket `url` alanları yerel aktarım yoluna çevrilir; sürüm alanları, paket SHA-256 değerleri ve indirilen paket baytları korunur. Güncelleme kontrolü veya yerel paket doğrulaması atlanmaz. Kalıcı proxy ortam değişkenleri eklenmez.

Gözlemci yaklaşık bir saniyede bir yalnızca kayıtlı kanalları kontrol eder. Arşiv iki kontrolde değişmeden kalmalı ve hiçbir Discord işlemi tarafından kullanılmamalıdır. Kayıt etkin olduğu sürece Discord kapansa da gözlemci çalışır. Windows oturum açılışında `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` altındaki `DiscordUnbound` değeriyle geri başlar.

**Yamala ve aç** sürümleri sayısal sıralar, en yenisini tekrar keşfedip doğrular ve yamalar; ardından **doğrudan o sürümün çalıştırılabilir dosyasını** açar. Önceden seçilen sürüm yamalanmasına rağmen `Update.exe` başka bir sürümü açabiliyordu. İstemcinin kendi yerel güncelleme ve paket bütünlüğü kontrolleri çalışmaya devam eder.

**Her gelecek sürüme otomatik uyum garantisi yoktur.** Güncelleyici yeni sürümü gözlemciden önce açarsa dosyalara zorla yama uygulanmaz ve Discord zorla kapatılmaz. Discord'u tamamen kapatıp Unbound üzerinden aç: en yeni sürüm açılmadan önce hazırlanır. Bilinmeyen bütünlük/fuse yapıları, değiştirilmiş arşiv/yedekler ve desteklenmeyen güncelleyiciler reddedilir. Fiziksel yeniden başlatma ve gerçek yeni ana sürüm yükseltmesi ayrıca doğrulanmalıdır.

## Uyumluluk ve doğrulama

| Alan | Doğrulanan durum |
| --- | --- |
| Hazır paket | Windows x64 |
| İncelenen istemci | Discord Stable 1.0.9264 / Electron 42.7.1 |
| Mesajlaşma ve ses | GoodbyeDPI kapalıyken gerçek kurulumda doğrulandı |
| Ağ geçidi | Geçerli TLS, WebSocket 101, HELLO opcode 10 |
| Ses kontrolü | `discord.media:2053`, WebSocket 101, HELLO opcode 8 |
| Güncelleme kontrolü | Yerel güncelleyici manifest kontrolünü geçerek ana ekranı açtı |
| Paket bütünlüğü | 19.137 baytlık resmi modül paketi indirildi; SHA-256 manifestle eşleşti |
| Otomatik testler | 39 Python + 14 Node.js testi |

**Satın alma kapsamı:** Nitro'nun genel sayfası ve Stripe'ın genel SDK bağlantısı izole Electron testinde açıldı. Gerçek satın alma, abonelik veya 3D Secure işlemi yapılmadı. Ödeme sağlayıcıları doğrudan bağlantıda kalır. Masaüstü yaması dış tarayıcıyı kapsamaz; isteğe bağlı web modu Windows proxy ayarını izleyen tarayıcılardaki Discord adreslerini kapsar. [Ayrıntılı uyumluluk incelemesi](docs/COMPATIBILITY.md).

Bu sonuçlar incelenen bilgisayar ve bağlantı içindir. Diğer internet sağlayıcıları ve Discord sürümleri için aynı sonucu garanti etmez. Windows ARM64/32 bit, macOS ve Linux desteği doğrulanmadı. Ekran paylaşımı/yayın Turkcell bağlantısında kullanıcı tarafından doğrulandı. Kameralı görüşme ve gerçek yeni bir ana Discord sürümünün baştan sona kurulması henüz test edilmedi. Hazır çalıştırılabilir dosya bu sürümde kod imzalı değildir.

Ağ engelinin IP düzeyinde olması veya ağın TLS kayıtlarını yeniden birleştirerek filtrelemesi farklı bir yöntem gerektirebilir. Yerel işlem ve DNS maliyeti vardır; sıfır gecikme iddiası yoktur.

## İnternet sağlayıcısı testleri

**✓ = denendi ve başarılı · boş hücre = denenmedi / ayrı doğrulama yok.** Sonuçlar bütün aboneler için garanti değildir; erişim türü ve bölge değişebilir. Türk Telekom sonucu kullanıcı bildirimi, Turkcell ise geliştiricinin bu projede kullandığı bağlantıdır. Turkcell erişiminin Superonline, Superbox veya mobil olduğu ayrıca belirtilmedi; sonuç bunların hepsine genellenmez. Son bildirim: **26 Ekim 2026**.

| Sağlayıcı | Durum | İstemci açılışı | Mesajlar | Ses | Tarayıcı web erişimi | Ekran paylaşımı / yayın |
| --- | --- | :---: | :---: | :---: | :---: | :---: |
| Türk Telekom (erişim tipi bildirilmedi) | ✓ Denendi — kullanıcı bildirimi | ✓ | ✓ | ✓ | | |
| Turkcell (erişim tipi bildirilmedi) | ✓ Denendi — geliştirici bağlantısı | ✓ | ✓ | ✓ | ✓ | ✓ |
| Vodafone Net / Ev İnterneti | Denenmedi | | | | | |
| Türksat Kablonet | Denenmedi | | | | | |
| TurkNet | Denenmedi | | | | | |
| Millenicom | Denenmedi | | | | | |
| D-Smart Net (Andromeda) | Denenmedi | | | | | |
| Netspeed | Denenmedi | | | | | |
| GıbırNet | Denenmedi | | | | | |
| Comnet | Denenmedi | | | | | |
| Fixnet | Denenmedi | | | | | |
| Extranet | Denenmedi | | | | | |
| Sadenet | Denenmedi | | | | | |
| Poyraz WiFi | Denenmedi | | | | | |
| Vodafone mobil | Denenmedi | | | | | |
| Türk Telekom mobil | Denenmedi | | | | | |

Türk Telekom'daki “her şey çalışıyor” bildirimi temel masaüstü kullanımına kaydedildi; ayrı tarayıcı testi belgelenmedi. Turkcell web sonucu önceki normal tarayıcı testine dayanır. Liste büyük sağlayıcıları ve ek topluluk test adaylarını kapsar; bütün lisanslı işletmecilerin veya pazar sırasının listesi değildir. [BTK pazar verileri](https://btk.tr/elektronik-haberlesme-pazar-verileri).

**Yukarıdaki tikler aşağıdaki aşamaları kapsamaz:**

| Aşama | Durum |
| --- | --- |
| Güncelleme manifesti ve örnek resmi modül paketi | ✓ Önceki Turkcell testinde paket özeti eşleşti |
| 0.3.0 kalıcı kayıt / en yeni sürümü önce yama | ✓ Otomatik senaryo testleri; canlı açılış ayrıca test kaydında |
| Bilgisayarı fiziksel olarak kapatıp açma | Denenmedi — oturum devamı testi fiziksel yeniden başlatma değildir |
| Yeni bir gerçek ana Discord sürümünün indirilip kurulması | Denenmedi — sentetik sürüm geçişi gerçek yükseltme değildir |
| Ekran paylaşımı / yayın | ✓ Turkcell — 26 Ekim 2026 canlı yeniden açılışından sonra kullanıcı doğruladı |
| Kameralı görüntülü görüşme | Denenmedi |
| Gerçek Nitro satın alma / abonelik / 3D Secure | Denenmedi |

Yeni bildirimde sağlayıcı, erişim türü (fiber/VDSL/kablo/mobil), Unbound/Discord sürümü ve başarılı **aşamaları** belirt. Tam adres, hesap bilgisi veya token paylaşma.

## Yedekleme ve sorun giderme

- Orijinal yedek: `resources/app.asar.discordunbound.original`
- Yama durumu ve dosya özetleri: `resources/app.asar.discordunbound.json`
- Çalışma durumu: `%LOCALAPPDATA%\DiscordUnbound\runtime.json`
- Kalıcı kanal / başlangıç yedeği: `%LOCALAPPDATA%\DiscordUnbound\managed.json` — kayıt kaldırılmadan silme.
- Gözlemci durumu: `%LOCALAPPDATA%\DiscordUnbound\watcher.json`
- Web modu yedeği: `%LOCALAPPDATA%\DiscordUnbound\web-state.json` — önceki proxy ayarlarını ve yerel kontrol anahtarını içerir; bu dosyayı hata bildirimine ekleme.

İlk yerel prototipte oluşturulan `.discordbridge.original` ve `.discordbridge.json` yedekleri de tanınır. Geri dönüş, mevcut dosyanın ve yedeğin özetini doğrular; değiştirilmiş bir arşivin üzerine eski dosyayı yazmaz. Yarım kalmış bir işlemde yedek ve durum dosyalarını silme.

**Güncelleme başarısız:** Discord'u tamamen kapat, güncel Discord Unbound sürümüyle yeniden başlat. **Ses bağlanmıyor:** hem ses kontrol bağlantısını hem UDP erişimini ayrı kontrol et; ses kontrolünün açılması tek başına UDP erişimini kanıtlamaz. Hata bildirirken Discord sürümünü, işletim sistemini ve anonimleştirilmiş hata açıklamasını ekle; hesap token'ı veya özel mesaj paylaşma.

Çalışma kaydı durum ve bağlantı sayaçları içerir; hesap token'ları, mesaj içerikleri ve trafik gövdeleri kaydedilmez.

## Geliştirme

Kaynak çalıştırma için Python 3.10+, JavaScript testleri için Node.js 22+ kullanılır. Hazır paket bunlara ihtiyaç duymaz.

```powershell
python src/app.py
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/hook.test.cjs
```

İsteğe bağlı, hesapsız canlı bağlantı testi:

```powershell
node tests/probe-live.cjs docs/live-result.json
```

Özel kurulum ve makine tarafından okunabilir çıktı:

```powershell
.\DiscordUnbound.exe --list --report installations.json
.\DiscordUnbound.exe --asar 'D:\Discord\app-1.0.9264\resources\app.asar' --patch --report patch-result.json
.\DiscordUnbound.exe --version --report version.json
.\DiscordUnbound.exe --web-start --report web-status.json
.\DiscordUnbound.exe --web-stop
.\DiscordUnbound.exe --web-status
```

Derleme:

```powershell
python -m pip install -r requirements-build.txt
python scripts/build.py
```

Derleme işlemi çalıştırılabilir dosyayı, dağıtım ZIP'ini ve SHA-256 özetlerini `dist/` dizinine üretir. Testler kurulu Discord'a dokunmadan sentetik arşivler ve yerel bağlantılar üzerinde çalışır.

## Geliştirici ve lisans

**Geliştirici: [Shazeus](https://github.com/shazeus)**

Proje kodu [MIT lisansı](LICENSE) ile sunulur. Kullanılan çalışma zamanı bileşenlerinin lisansları `third-party/` dizinindedir. Discord adı ve Discord'dan uyarlanan sembol ilgili hak sahiplerine aittir; proje Discord ile bağlantılı veya Discord tarafından onaylanmış değildir. Proje lisansı bu markalar üzerinde ek hak vermez.

[Teknik inceleme](docs/RESEARCH.md) · [Test kayıtları](docs/TEST-RESULTS.md) · [İstiklal Marşı alıntısının kaynağı](https://www.tbmm.gov.tr/milletvekili/UyeGenelKurulKonusmalariDetay?eid=143116)
