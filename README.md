<p align="center">
  <img src="assets/discord-unbound-logo.png" alt="Discord Unbound" width="760">
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
- **Uzak VPN sunucusu gerektirmez:** bilgisayarın genel trafiğini bir tünele almaz; sistemin yönlendirme, DNS, proxy, güvenlik duvarı ve sertifika ayarlarını değiştirmez.
- **TLS kayıt bölümleme:** ilk `ClientHello` mesajının baytlarını koruyarak TLS kayıtlarını küçük parçalara böler. Mesajlaşma bağlantısında TLS çözülmez ve sertifika doğrulaması kapatılmaz.
- **Yerel güncelleyici uyarlaması:** resmi manifest ve paket isteklerini aynı bağlantı katmanından geçirir; paket içeriğini ve manifestteki SHA-256 alanlarını korur.
- **Ses bağlantısı desteği:** `discord.media` üzerindeki ses kontrol bağlantısının verdiği TLS portunu korur; 2053 portu ayrıca test edilmiştir. UDP ses paketleri doğrudan gider.
- **Geri alınabilir yama:** orijinal arşiv yedeği, dosya özeti denetimi, işlem kilidi ve orijinale dönüş içerir.
- **Sürüm gözlemcisi:** yeni kurulum dizinlerini izler ve uygun, kullanılmayan sürümlere yamayı yeniden uygulamayı dener.

## İndir ve çalıştır

**[En güncel sürümü indir](https://github.com/shazeus/discord-unbound/releases/latest)**

1. Sürüm sayfasındaki `DiscordUnbound-windows-x64.zip` paketini indirip bir klasöre çıkar.
2. Discord'u sistem tepsisindeki simgesinden **tamamen kapat**.
3. `DiscordUnbound.exe` dosyasını aç.
4. Listeden kurulumunu seç ve **Yamala ve aç** düğmesine bas.

Hazır pakette Python veya Node.js kurulu olması gerekmez. Yama uygulandıktan sonra mevcut Discord kısayolu da o sürümü açabilir. Güncellemelerin izlenmesi için uygulamayı Discord Unbound üzerinden başlatmak önerilir.

Geri dönmek için Discord'u tamamen kapatıp **Orijinale dön** seçeneğini kullan. Bu işlem, gözlemcinin aynı kuruluma yamayı yeniden uygulamasını da durdurur.

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

Gözlemci yaklaşık üç saniyede bir sürüm dizinlerini kontrol eder. Arşiv iki kontrolde değişmeden kalmışsa ve ilgili sürümü kullanan Discord işlemi yoksa yama uygulanabilir. Discord kapandıktan sonra gözlemci üç dakika içinde çıkar; Windows başlangıcına servis veya zamanlanmış görev eklenmez.

**Her gelecek sürüme otomatik uyum garantisi yoktur.** Güncelleyicinin yeni sürümü başlatmasıyla gözlemcinin yamalaması arasında yarış oluşabilir. Yeni sürüm yamasız açılırsa Discord'u kapatıp Discord Unbound üzerinden yeniden başlat. Yeni bir arşiv yapısı, güncelleyici arayüzü veya bütünlük zorlaması kod uyarlaması gerektirebilir.

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
| Otomatik testler | 19 Python + 14 Node.js testi |

**Satın alma kapsamı:** Nitro'nun genel sayfası ve Stripe'ın genel SDK bağlantısı izole Electron testinde açıldı. Gerçek satın alma, abonelik veya 3D Secure işlemi yapılmadı. Ödeme sağlayıcıları doğrudan bağlantıda kalır. İşletim sistemi tarayıcısında açılan akışlar bu uygulamanın PAC ayarını kullanmaz. [Ayrıntılı uyumluluk incelemesi](docs/COMPATIBILITY.md).

Bu sonuçlar incelenen bilgisayar ve bağlantı içindir. Diğer internet sağlayıcıları ve Discord sürümleri için aynı sonucu garanti etmez. Windows ARM64/32 bit, macOS ve Linux desteği doğrulanmadı. Video, ekran paylaşımı ve daha yeni bir ana Discord sürümünün baştan sona kurulması henüz test edilmedi. Hazır çalıştırılabilir dosya bu sürümde kod imzalı değildir.

Ağ engelinin IP düzeyinde olması veya ağın TLS kayıtlarını yeniden birleştirerek filtrelemesi farklı bir yöntem gerektirebilir. Yerel işlem ve DNS maliyeti vardır; sıfır gecikme iddiası yoktur.

## Yedekleme ve sorun giderme

- Orijinal yedek: `resources/app.asar.discordunbound.original`
- Yama durumu ve dosya özetleri: `resources/app.asar.discordunbound.json`
- Çalışma durumu: `%LOCALAPPDATA%\DiscordUnbound\runtime.json`
- Gözlemci durumu: `%LOCALAPPDATA%\DiscordUnbound\watcher.json`

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
