# Design Context — نظام مكتب التوظيف

> ملف سياق تصميمي جاهز للصق في System Prompt لأي نموذج ذكاء اصطناعي ينتج واجهات Frontend جديدة.
> الهدف: أن أي شاشة جديدة تُولَّد تخرج بنفس هوية النظام الحالية — نفس الألوان، نفس الفونت، نفس الإيقاع البصري — بدون تطرّف لوني أو تناقض بين الصفحات.

---

## 1. هوية المنتج

```
نظام مكتب توظيف عربي — RTL — يعمل على إدارة دورة التوظيف الكاملة:
طلبات الشركات ← المتقدمون ← طلبات التوظيف ← المتابعة ← الحركة المالية.

الإحساس المطلوب: "مكتب عمليات هادئ" (calm operations desk) — لا مبهرج، لا مزدحم.
الجمهور: موظف ومحاسب ومدير مكتب يحتاجان شاشة يستخدمونها لساعات طويلة.
```

---

## 2. لوحة الألوان الفعلية

الألوان مأخوذة حرفيًا من الكود (`#xxxxxx` → اسم دور):

### 2.1 السطح (Surfaces)
| الدور | اللون | ملاحظة الاستخدام |
|---|---|---|
| Page Background | `#f5f6f3` | خلفية الصفحة الرئيسية |
| Top Header Glass | `#f8f9f6` / 95% + backdrop-blur | الشريط العلوي الثابت |
| Card Surface | `#fffdfa` | خلفية البطاقات والأشكال |
| Subtle Band | `#fafbf8` | خلفية رؤوس الجداول |
| Sidebar Surface | `#1e303d` | خلفية القائمة الجانبية اليمين |
| Sidebar Hover | `#223442` | خلفية العنصر عند المرور |
| Sidebar Active | `#263746` | خلفية العنصر النشط |
| Sidebar Footer Hover | `#2c4351` | تمرير الإعدادات/البروفايل |

### 2.2 النص (Text)
| الدور | اللون |
|---|---|
| Text Primary | `#29404d` |
| Heading Strong | `#263d49` |
| Heading Stronger | `#2c4651` |
| Text Body | `#405a63` |
| Text Secondary | `#51666c` |
| Text Muted | `#647984` |
| Text Tertiary | `#7d918f` |
| Text Hint | `#8b999a` |
| Text Footer | `#9aa6a3` |

Text on dark sidebar: `#dce5e7`, `#edf2f0`, `#fff7ec`, `#9aacb9`, `#718894`.

### 2.3 الحدود والظلال
| الدور | اللون |
|---|---|
| Border Default | `#e5e5e1` |
| Border Soft | `#e1e4df` / `#ecece7` |
| Border Stronger | `#e2e4df` / `#e4e5e0` |
| Border Accent (active item) | `#d49b55` |

Shadow levels:
- Card resting: `shadow-[0_5px_18px_rgba(43,58,67,0.04)]`
- Card hover: `shadow-[0_10px_24px_rgba(43,58,67,0.09)]`
- Dropdown: `shadow-[0_15px_35px_rgba(39,57,65,0.14)]`

### 2.4 اللون البرتقالي/الذهبي — Brand Amber (للاستخدام المحدد)
| الاستخدام | اللون |
|---|---|
| Logo icon background | `#d69e5b` |
| Active item accent border | `#d49b55` |
| Notification dot | `#d68f57` |
| Follow-up orange tint | `#d59f59` |
| Orange text on light | `#a06b25` / `#b47c31` |
| Soft amber bg | `#fcf2df` / `#fcfaf5` / `#f8ecd8` |

### 2.5 ألوان الحالات (Status Palette) — تُستخدم بشكل ثابت وسياقي
| الحالة | خلفية | نص/لون قوي |
|---|---|---|
| نجاح / مقبول / قبض | `#e6f3ed` أو `#e1f3ec` | `#28745c` / `#17765e` / `#4d967d` / `#4d9e81` |
| معلومة / قيد المراجعة / قيد التنفيذ | `#e9eef8` أو `#e8eefb` | `#466b9c` / `#335a99` / `#5b82b3` |
| تنبيه / مفتوح / متابعة | `#fcf2df` أو `#f8ecd8` | `#a06b25` / `#d39c55` / `#d8a55b` |
| خطر / مرفوض / قراءة خاطئة | `#f4dddd` | `#a95755` / `#c98287` / `#bb6d5e` |
| محايد / محاسبي / دفع | موف/أحمر فاتح `#f1e6e1` / `#fdf9f7` | `#875b53` / `#bb786a` / `#9e6f8b` |

## 3. الخط (Typography)

```
Primary (Arabic): Tajawal, weights [400, 500, 700, 800]
Fallback chain: 'Tajawal','Noto Sans Arabic', system-ui, sans-serif
```

| الدور | الحجم | الوزن |
|---|---|---|
| Display hero | 25–28px | bold (tracking-tight) |
| H1 page heading | 18px | bold |
| H2 section heading | 14–16px | bold |
| H3 sub-section | 13–14px | semibold |
| Body | 12–13px | regular/medium |
| Helper / Caption | 10–11px | regular |
| Micro | 9–10px | medium |

قاعدة عامة للقراءة:
- لا تزيد عن 13px في البطاقات والجداول.
- الرقم في البطاقة الإحصائية = 28px Tajawal Bold.
- النص العربي دائمًا right-align داخل البطاقات.

## 4. الأبعاد والـLayout

### 4.1 Sidebar
- ثابت على اليمين (RTL).
- عرض واسع: 268px.
- عرض مطوي: 76px.
- Header height: 78px.
- Transition: `transition-[width] duration-300`.
- Sticky على كل الشاشات الكبيرة، drawer على الموبايل.

### 4.2 Top Header
- ارتفاع: 78px.
- Sticky top.
- خلفية `#f8f9f6/95` + `backdrop-blur-md`.
- Border bottom: 1px `#e5e5e1`.
- Padding أفقي: 20–32px.

### 4.3 Content Area
- Container max-width: `max-w-[1440px]`.
- Padding: `px-5 md:px-8 py-7`.
- مسافة بين الأقسام: 24–28px.

### 4.4 الشبكة (Grid)
- 4-column stats على desktop: `grid-cols-1 sm:grid-cols-2 xl:grid-cols-4`.
- التفاصيل الرئيسية: `xl:grid-cols-[minmax(0,1.45fr)_minmax(330px,0.85fr)]`.
- النشاطات والـfollow-ups: `xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]`.

### 4.5 المسافات
- بين عناصر داخل بطاقة: 12–16px.
- بين بطاقات متجاورة: 20px (gap-5).
- بين أقسام: 28px (mt-7).

## 5. نصف القطر — Radius (مهم جدًا)

النظام يستخدم نصف قطر صغير جدًّا لتجنّب الإحساس الطفولي:

| العنصر | Radius |
|---|---|
| Card | 0 (حاد الزوايا) أو على الأكثر `rounded-[2px]` |
| Sticky header buttons | `rounded-md` (6px) |
| Icon boxes | `rounded-lg` (8px) |
| Avatar circles | `rounded-full` (مقبول فقط للأفاتارات والشعارات) |
| Badges | 0 أو `rounded-full` صريح (نادر) |
| Inputs | 0 إلى `rounded-md` |

> ❌ القاعدة الذهبية: لا تستخدم `rounded-xl` أو `rounded-2xl` أو `rounded-3xl` على الواجهة. النظام حاد الزوايا بطبيعته.

## 6. الأيقونات (Iconography)

```
- SVG فقط. ممنوع emoji تمامًا.
- المكتبة: lucide-react.
- الحجم المعتاد: 17–19px داخل القوائم والبطاقات، 14–17px داخل headers.
- Stroke: رفيع (الوضع الافتراضي لـ lucide).
- اللون: يتبع النص المجاور (currentColor) غالبًا، مع override واحد للون البرتقالي على العنصر النشط.
```

أمثلة محجوزة لكل وحدة:
- نظرة عامة: LayoutDashboard
- طلبات الشركات: ClipboardList
- طلبات التوظيف: FileCheck2
- المتقدمون: UsersRound
- الوظائف: BriefcaseBusiness
- الشركات: Building2
- المتابعات: CalendarDays
- السندات: ReceiptText
- تصنيفات السندات: WalletCards
- الإدارة: ShieldCheck
- المالية: CircleDollarSign
- الإشعارات: Bell
- الإعدادات: Settings2

## 7. الأزرار والإدخال

### 7.1 Primary button (العمل الرئيسي)
```
bg-[#2d5664] text-[#fff9f0]
hover:bg-[#234854]
shadow-[0_4px_12px_rgba(45,86,100,0.18)]
px-4 py-2.5 text-[12px] font-semibold
```
بدون radius إلا `rounded-md` عند الضرورة.

### 7.2 Icon button (في الـHeader أو الـTable)
```
h-9 w-9 inline-flex items-center justify-center
border border-[#e1e4df] bg-[#fffdfa] text-[#607681]
hover:border-[#c7d3ce] hover:text-[#294b59]
rounded-md
```

### 7.3 Active Sidebar Item
```
border-r-2 border-[#d49b55] bg-[#263746] text-[#fff8ed]
icon color: text-[#e1ad6a]
badge: bg-[#405565] text-[#f6d49d]
```

### 7.4 Inputs
```
h-12 (دخول/صفحات) أو h-9 (في شريط البحث ضمن الـheader)
bg-[#fbfcfa] border-[#dfe4e0]
focus:border-[#7d9b9a] focus:ring-4 focus:ring-[#dce9e5]
error: border-[#c98287] focus:ring-[#f4dddd]
```

## 8. الـBadges وشارة الحالة

`StatusBadge` هو مكوّن موحّد لكل حالات النظام:

| الحالة | Tone الكامل |
|---|---|
| مفتوح | `bg-[#fcf2df] text-[#a06b25]` |
| قيد التنفيذ / قيد المراجعة | `bg-[#e9eef8] text-[#466b9c]` |
| مقبول / مكتمل | `bg-[#e6f3ed] text-[#28745c]` |
| مرفوض / ملغي | `bg-[#f4dddd] text-[#a95755]` |
| سند قبض | `bg-[#f8fbf8] border-[#e4eee8] text-[#3f665a]` |
| سند دفع | `bg-[#fdf9f7] border-[#f1e6e1] text-[#875b53]` |

البادج: `px-2.5 py-1 text-[11px] font-medium` + نقطة دائرة 6px بلون النص بجوار النص.

## 9. الجداول

- خلفية الرأس: `#fafbf8`.
- Font inside table: `text-[11px]`.
- Heading cells: `text-[10px] font-medium text-[#91a09f]`.
- الصفوف: `divide-y divide-[#f0f0ec]`.
- Hover row: `hover:bg-[#fbfcf9]`.
- لا مزيد من padding: `px-5 py-3.5` للخلايا.
- اتجاه الجدول: `text-right` RTL.

## 10. الحركة (Motion Language)

- Sidebar collapse: `transition-[width] duration-300`.
- Hover transitions: `transition-all duration-200`.
- Quick open/close panels: `transition-all duration-300`.
- Buttons/Quick Action Dropdown: بدون easing مبالغ — فقط `ease` أو `ease-out`.
- لا keyframes معقدة، لا scroll triggers داخل شاشات الإدارة.

## 11. RTL

- كل القوالب تبدأ بـ `<html lang="ar" dir="rtl">`.
- `dir="rtl"` على `<body>` أيضًا.
- Sidebar على اليمين دائمًا.
- أيقونات الأسهم تُعكَس تلقائيًا (`ChevronLeft` يُستخدم بدلاً من ChevronRight للعودة في RTL).
- `border-r-*` بدل `border-l-*` لتمييز العنصر النشط.
- `text-right` افتراضي للمحتوى العربي.

## 12. Dark Mode

النظام مُهيّأ (`dark:` prefixes) لكنه غير مفعّل افتراضيًا. القيم:

```
dark: bg: #0f172a / #111827
dark: card: #1e293b
dark: border: #334155
dark: text: #cbd5e1 / #f1f5f9
dark: input bg: #0b1220
```

عند بناء أي شاشة جديدة يجب إضافة dark prefixes في وقت واحد، خصوصًا للبطاقات والـinputs.

## 13. قاعدة البيانات والسياق الدلالي

يجب أن تقرأ الشاشة دائمًا من دورة العمل:

```
Company → CompanyJobRequest (الحالة: مفتوح/مكتمل/ملغي)
                  ↓
             Application ← Applicant  (الحالة: جديد/قيد المراجعة/مقبول/مرفوض)
                  ↓
                 FollowUp + Voucher (قبض/دفع) + VoucherCategory

User Role: مدير / موظف / محاسب
```

أي صفحة جديدة يجب أن تخدم وحدة من هذه الوحدات. لا تختلق صفحات خارج هذا المنطق.

## 14. قواعد تجنّب (Anti-patterns)

❌ لا تستخدم ألوانًا تُخرج عن اللوحة:
- لا أحمر فاقع (`#ef4444`)، لا أزرق مشعّع (`#3b82f6`)، لا بنفسجي مبالغ.
- استبدلها: `#a95755` للأخطاء، `#466b9c` للمعلومات، `#9e6f8b` للوضع المحاسبي.

❌ لا تستخدم:
- `rounded-xl / 2xl / 3xl`
- glassmorphism مبالغ، gradients ملونة.
- emojis داخل الواجهة.
- خط Inter أو Roboto للنص العربي — استخدم Tajawal دائمًا.

❌ لا تختلق وحدات جديدة:
- لا تضيف "إدارة الفروع" أو "إدارة الخطابات" ما لم تكن في قاعدة البيانات.

❌ لا تصنع صفحتين بنفس البيانات بألوان متضاربة:
- إذا كانت صفحة "طلبات الشركات" فاتحة ودافئة، صفحة "طلبات التوظيف" يجب أن تكون بنفس الإيقاع. التمييز بين الصفحات يجب أن يكون هرميًا (نفس النظام اللوني).

## 15. نبرة التصميم (Tone Summary)

> "مكتب مسار للتوظيف" لوحة أعمال زرقة-خشبية داكنة (sidebar) مع خلفية عاجية فاتحة ومسحة برتقالية-ذهبية واحدة فقط للتركيز على الإجراءات النشطة. النص الهادئ readable لساعات، الزوايا حادة، الإيقاع مكثّف لكن غير مزدحم. كل صفحة جزء من نفس الجملة البصرية، لا stand-alone page.

---

## 16. System Prompt المقترح للصق في أي نموذج ذكاء اصطناعي

```text
You are a Frontend Engineer building screens that match an existing Arabic RTL
operations dashboard called "مكتب مسار للتوظيف".

Visual rules (mandatory):
- Direction: RTL, lang="ar". Default font: Tajawal, fallback chain
  'Tajawal','Noto Sans Arabic',system-ui,sans-serif.
- Page background: #f5f6f3. Cards: #fffdfa on top of #e1e4df 1px borders.
- Sidebar on the right, fixed, dark slate #1e303d, collapses 268px <-> 76px
  in 300ms.
- Sticky top header #f8f9f6/95 + backdrop-blur, height 78px.
- Brand accent (sparingly): #d49b55 / #d69e5b.
- Status palette: success #e6f3ed/#28745c; info #e9eef8/#466b9c;
  warning #fcf2df/#a06b25; danger #f4dddd/#a95755; neutral-finance #fdf9f7/#875b53.
- Text: primary #29404d, secondary #51666c, muted #7d918f, hint #8b999a.
- Buttons: primary uses #2d5664 with #234854 on hover. Icon buttons
  neutral outlined #e1e4df. Inputs h-12 with focus ring #dce9e5.
- Radii: avoid rounded-xl / 2xl / 3xl. Use 0–6px max for cards, 8px max
  for icon boxes. The system is sharp-edged by default.
- Icons: SVG only via lucide-react. No emoji. 17–19px in lists/cards,
  14–17px in headers.
- Animations: only transition-[width] duration-300 (sidebar),
  transition-all duration-200 (hover). No decorative motion.
- Dark mode: include dark: variants in every new card/input/border,
  using bg-[#0f172a]/[#1e293b]/[#cbd5e1].
- Layout: container max-w-[1440px], px-5 md:px-8 py-7. Section gap 28px.
- Domain semantics: pages only for office-mod-desktop modules — Company,
  CompanyJobRequest, Applicant, Application, FollowUp, Voucher, VoucherCategory,
  User. Do not invent new domains.

Required deliverables per request:
1. Reusable components, no duplicated structures.
2. Semantic HTML (header/main/aside/nav), accessible labels and roles.
3. Realistic Arabic content (no Lorem ipsum), reflecting the schema above.
4. No emojis, no inline styles, no repeating palette across the page.
```

---

## 17. مرجع سريع — Tailwind Classes الشائعة

```html
<!-- Page wrap -->
<div dir="rtl" class="min-h-[100dvh] bg-[#f5f6f3] font-['Tajawal','Noto_Sans_Arabic',sans-serif] text-[#29404d]">

<!-- Sidebar -->
<aside class="fixed inset-y-0 right-0 z-30 flex flex-col bg-[#1e303d] text-[#dce5e7]
              w-[268px] transition-[width] duration-300" data-collapsed="w-[76px]">

<!-- Active item -->
<button class="border-r-2 border-[#d49b55] bg-[#263746] text-[#fff8ed]">
  <Icon class="h-[17px] w-[17px] text-[#e1ad6a]" />
</button>

<!-- Inactive item -->
<button class="border-r-2 border-transparent text-[#9aacb9]
              hover:border-[#486174] hover:bg-[#223442] hover:text-[#f4eee5]">

<!-- Card -->
<article class="border border-[#e4e5e0] bg-[#fffdfa]
               shadow-[0_5px_18px_rgba(43,58,67,0.035)]">

<!-- Status badge -->
<span class="inline-flex items-center gap-1.5 bg-[#e6f3ed] text-[#28745c]
             px-2.5 py-1 text-[11px] font-medium">
  <span class="h-1.5 w-1.5 rounded-full bg-current" />مقبول
</span>

<!-- Primary action -->
<button class="bg-[#2d5664] px-4 py-2.5 text-[12px] font-semibold text-[#fff9f0]
               hover:bg-[#234854]
               shadow-[0_4px_12px_rgba(45,86,100,0.18)]">

<!-- Table row -->
<tr class="transition-colors hover:bg-[#fbfcf9]">

<!-- Input -->
<input class="h-12 w-full border border-[#dfe4e0] bg-[#fbfcfa] px-4
              focus:border-[#7d9b9a] focus:ring-4 focus:ring-[#dce9e5]" />
```
