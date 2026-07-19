from escpos.printer import Usb

p = Usb(0x0416, 0x5011, 0)
p.text("Hello World\n")
# p.image("logo.gif")
p.barcode('4006381333931', 'EAN13', 64, 2, '', '')
p.cut()
