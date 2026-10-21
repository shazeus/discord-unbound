# Sürüm geçmişi

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
