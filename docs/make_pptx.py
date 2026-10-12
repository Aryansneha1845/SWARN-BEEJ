"""Build Screen-1 PPTX. Run: python docs/make_pptx.py"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

GREEN = RGBColor(0x0F, 0x3D, 0x24)
GOLD = RGBColor(0xF2, 0xB7, 0x05)
CREAM = RGBColor(0xFF, 0xFA, 0xF0)
DARK = RGBColor(0x1D, 0x1C, 0x16)
GREY = RGBColor(0x41, 0x49, 0x42)
FONT = "Nirmala UI"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank = prs.slide_layouts[6]


def add_bg(slide):
    bg = slide.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = CREAM
    bg.line.fill.background()
    bar = slide.shapes.add_shape(1, 0, 0, prs.slide_width, Inches(0.28))
    bar.fill.solid()
    bar.fill.fore_color.rgb = GREEN
    bar.line.fill.background()


def add_slide(title, points, footer="SWARN-BEEJ • SEVA FIRST RYIC 2026 • Local REG-001"):
    s = prs.slides.add_slide(blank)
    add_bg(s)
    tx = s.shapes.add_textbox(Inches(0.7), Inches(0.6), Inches(11.9), Inches(1.0))
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.name = FONT
    p.font.color.rgb = GREEN
    bx = s.shapes.add_textbox(Inches(0.7), Inches(1.7), Inches(11.9), Inches(4.8))
    bf = bx.text_frame
    bf.word_wrap = True
    for i, pt in enumerate(points):
        p = bf.paragraphs[0] if i == 0 else bf.add_paragraph()
        p.text = "•  " + pt
        p.font.size = Pt(22)
        p.font.name = FONT
        p.font.color.rgb = DARK
        p.space_after = Pt(10)
    ft = s.shapes.add_textbox(Inches(0.7), Inches(6.8), Inches(11.9), Inches(0.5))
    fp = ft.text_frame.paragraphs[0]
    fp.text = footer
    fp.font.size = Pt(14)
    fp.font.name = FONT
    fp.font.color.rgb = GREY
    return s


# 1. Title
s = prs.slides.add_slide(blank)
add_bg(s)
t = s.shapes.add_textbox(Inches(0.7), Inches(1.6), Inches(11.9), Inches(2.2))
tf = t.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.text = "🌾 स्वर्ण-बीज (SWARN-BEEJ)"
p.font.size = Pt(54)
p.font.bold = True
p.font.name = FONT
p.font.color.rgb = GREEN
p = tf.add_paragraph()
p.text = "नकली बीज/कीटनाशक पकड़ो — स्कैन, बिल, शिकायत"
p.font.size = Pt(28)
p.font.name = FONT
p.font.color.rgb = DARK
d = s.shapes.add_textbox(Inches(0.7), Inches(4.2), Inches(11.9), Inches(2.0))
df = d.text_frame
df.word_wrap = True
for line in ["SEVA FIRST RYIC 2026 • Local Track REG-001 (ग्राम/पंचायत, कृषि)",
             "Category-II: Diploma & Higher Education • Solo + Mentor",
             "TRL 2 → 6 • लागत < ₹2,000 • हिंदी PWA, ऑफ़लाइन"]:
    p = df.add_paragraph() if len(df.paragraphs[0].runs) else df.paragraphs[0]
    p.text = "•  " + line
    p.font.size = Pt(22)
    p.font.name = FONT
    p.font.color.rgb = DARK

add_slide("1. समस्या",
          ["पंजाब-हरियाणा के छोटे किसान नकली बीज/कीटनाशक ले लेते हैं — पैक असली लगता है, QR नकली, बिल नहीं मिलता।",
           "फसल 40–90% तक खराब (सीरसा ग्वार केस 2012, NCR फ़रीदाबाद केस)।",
           "बिल न होने से मुआवज़ा भी नहीं मिलता — दोहरी मार।"])
add_slide("2. कहाँ देखा",
          ["कॉलेज के पास 2–3 कृषि दुकानें + 1 गाँव (दिल्ली-NCR किनारा / सिरसा लिंक)।",
           "[फोटो लगाएँ: दुकान बोर्ड + पैकेट शेल्फ]",
           "क्षेत्र: उत्तरी क्षेत्र (DTU) — दिल्ली, हरियाणा, पंजाब।"])
add_slide("3. साक्ष्य (Evidence)",
          ["[फोटो लगाएँ: 15 पैकेट front-back + batch/expiry close-up]",
           "[फोटो लगाएँ: 5 बिल + दुकान बोर्ड]",
           "हर फोटो: तारीख + दुकान नाम से फ़ाइल नाम (field-evidence/ देखें)।"])
add_slide("4. कौन प्रभावित, कितने",
          ["1 दुकान ≈ 200 किसान/सीज़न; ज़िले में हज़ारों।",
           "PIB 11-Feb-2025 (2023-24): 1,33,588 बीज नमूनों में 3,630 घटिया; 1,81,153 उर्वरक में 8,988 अमानक; 80,789 कीटनाशक में 2,222 नकली।",
           "बठिंडा (अग-2024) व हरियाणा (जन-2026) में नकली स्टॉक ज़ब्त — खबर कटिंग संलग्न करें।"])
add_slide("5. किसान से बातचीत",
          ["10 किसान, 2-मिनट बात: 90% बिल नहीं लेते, QR जाँचना नहीं आता।",
           "[वीडियो/ऑडियो लगाएँ: नाम + गाँव + कब नुकसान — सहमति पत्र के साथ]",
           "सीख: ऐप हिंदी + ऑफ़लाइन + 3 बटन से ज़्यादा नहीं।"])
add_slide("6. मौजूदा व्यवस्था + कमी",
          ["SATHI पोर्टल (सरकारी) है — पर B2B/अंग्रेज़ी, किसान के फोन पर ऑफ़लाइन हिंदी में नहीं चलता।",
           "डीलर सूची बंद; QR वेरिफिकेशन किसान तक नहीं पहुँचता।",
           "[स्क्रीनशॉट लगाएँ: SATHI बनाम SWARN-BEEJ side-by-side]।"])
add_slide("7. समाधान — 3 काम",
          ["1. स्कैन और सच: ब्रांड+बैच+QR → हरा/पीला/लाल + भरोसा% + हिंदी कारण + आवाज़।",
           "2. बिल सुरक्षा: बिल फोटो + दुकान + तारीख सेव — शिकायत का सबूत।",
           "3. शिकायत ड्राफ्ट: 1-टैप हिंदी अर्जी — कॉपी/WhatsApp/PDF, हेल्पलाइन 14447।"])
add_slide("8. नया क्या है",
          ["नकली QR पकड़: एक ही QR दो पैकेटों पर → reused चेतावनी (फोटोकॉपी वाला छेद बंद)।",
           "बिल को सबूत-शृंखला बनाना (बिना बिल मुआवज़ा नहीं — सीरसा केस 5 साल लटका)।",
           "SATHI का last-mile: हिंदी आवाज़ + ऑफ़लाइन + safe-default (अज्ञात = पीला, कभी झूठा हरा नहीं)।"])
add_slide("9. प्रवाह",
          ["स्कैन → संकेत (हरा/पीला/लाल) → बिल सेव → शिकायत ड्राफ्ट → अधिकारी।",
           "फसल डॉक्टर: पत्ती फोटो → बीमारी अंदाज़ा + इलाज + वीडियो + मौसम/ज़ोन।",
           "[चित्र लगाएँ: flow diagram — हाथ से बना भी चलेगा]।"])
add_slide("10. लागत-लाभ",
          ["किसान के लिए मुफ़्त; होस्टिंग < ₹2,000।",
           "1 एकड़ में ≈ ₹12,000 का नुकसान बचता है (ग्वार 7–8 क्विंटल @₹30k, 40% हानि)।",
           "स्केल: पंजाब-हरियाणा → हिमाचल सेब, उत्तराखंड मसाला बीज (वही इंजन)।"])
add_slide("11. 75-दिन योजना",
          ["सप्ताह 1: सर्वे + PPT (Screen-1) + 15 दुकान/पैकेट साक्ष्य।",
           "सप्ताह 2: MVP (3 फीचर) + 60-सैंपल accuracy जाँच।",
           "सप्ताह 3: 15-किसान फील्ड टेस्ट + 5-मिनट वीडियो।",
           "सप्ताह 4: सुधार + अंतिम रिपोर्ट + जूरी डेमो।"])
add_slide("12. टीम + ज़रूरतें",
          ["Solo + 1 mentor (प्रोफ़ेसर/कृषि अधिकारी पत्र — [पत्र लगाएँ])।",
           "चाहिए: फोन, दुकान अनुमति, SATHI सूची अपडेट, 60 पैकेट टेस्ट-सेट।",
           "Entry TRL-2 → लक्ष्य TRL-6 (डेमो-सेट 100%, फील्ड लक्ष्य 85%)।"])

out = "docs/SWARN-BEEJ_Screen-1.pptx"
prs.save(out)
print("saved:", out, "| slides:", len(prs.slides._sldIdLst))
