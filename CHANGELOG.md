# Sürüm geçmişi

## 0.3.0 — 26 Ekim 2026

- Kullanıcı oturumunda geri başlayan kalıcı gözlemci ve doğrulanmış başlatıcı kopyası.
- Üç dakikalık kapanma sınırı kaldırıldı; yalnızca kayıtlı kanallar izleniyor.
- En yeni sürüm açılmadan önce yamalanıyor; farklı sürümü seçebilen Update.exe aktarımı kaldırıldı.
- Mevcut Discord başlangıç tercihi korunuyor; sahiplik denetimli kaldırma düğmesi.
- Türkçe/İngilizce sağlayıcı ve test aşaması tabloları.
- 39 Python + 14 Node.js testi. Fiziksel yeniden başlatma / gerçek ana sürüm yükseltmesi ayrıca doğrulanmalı.


## 0.2.0 — 21 Ekim 2026

- Normal tarayıcılar için isteğe bağlı, yalnızca Discord'a yönlenen Windows PAC modu.
- Tek dosyalık pakette bağımsız yerel Python aktarımı; ayrı Node.js gerekmez.
- Eski PAC/manual proxy kuralını koruma, kalıcı durum yedeği ve sahiplik denetimli geri dönüş.
- Yardımcı zorla kapatıldığında ayarları geri yükleyen bağımsız kurtarma gözeticisi.
- Web erişimini aç/kapat ve varsayılan tarayıcıda Discord'u aç düğmeleri.
- 30 Python + 14 Node.js testi; gerçek Brave sekmesi, Windows PAC ve normal/zorla kapanış geri dönüşü doğrulandı.

## 0.1.1 — 21 Ekim 2026

- Yerel proxy'ye gelen HTTP Discord GET/HEAD bağlantılarının 404 vermesi düzeltildi;
  aynı yol ve sorgu ile HTTPS'ye 307 yönlendirmesi yapılır.
- Resmi `discord.gift` ve `dis.gd` bağlantıları için tam alan adı desteği eklendi.
- Stripe, PayPal ve diğer ödeme sağlayıcılarının doğrudan bağlantıda kalması
  testlerle korundu; yeni bağlantı alanları güncelleyici kaynaklarına eklenmedi.
- Nitro ve dış tarayıcı/3D Secure kapsamı belgelendi. Satın alma yapılmadı.
- 19 Python ve 14 Node.js testi geçti. İzole Electron'da Nitro genel sayfası,
  Stripe SDK'sı ve resmi paket bütünlüğü doğrulandı.

## 0.1.0 — 21 Ekim 2026

Discord Unbound'un ilk yayımlanan sürümü.

- Orijinal Discord için geri alınabilir ASAR başlangıç yaması.
- Yerel TLS kayıt bölümleme ve Discord alan adlarına özel bağlantı kuralları.
- Resmi güncelleyici için manifest ve paket aktarım uyarlaması.
- `discord.media` ses kontrolü için 2053 dahil geçerli TLS portları.
- Dosya özeti doğrulaması, orijinal yedek ve geri dönüş.
- Yeni sürüm dizinlerini izleyen oturumluk gözlemci.
- Kırmızı/beyaz Discord Unbound logosu ve uygulama simgesi.
- Türkçe ana belge ve bağlantılı İngilizce belge.

Windows x64 paketi ve 31 otomatik test doğrulandı. Mesajlaşma ve ses, incelenen
kurulumda GoodbyeDPI kapalıyken çalıştı. Diğer ağlar, ekran paylaşımı ve daha yeni
bir ana Discord sürümünün kurulması için ayrıca doğrulama gerekir.
