# Onebed Style Guide for Developers

## Color Definitions

### Primary Colors
```css
--color-navy: #2A2660;
--color-navy-accent: #8C9EFF;
```

### Navy Color Scale
```css
--color-navy: #2A2660;
--color-navy-2: #474195;
--color-navy-3: #554FB0;
--color-navy-4: #635CCA;
--color-navy-accent: #8C9EFF;
```

### Accent Colors
```css
--color-accent-1: #FFCD83;  /* Yellow/Gold accent */
--color-accent-2: #FF5252;  /* Red accent */
```

### Text Colors
```css
--color-text-navy: #2A2660;
--color-text-body: #707074;
--color-text-body-light: #B0B0B5;
--color-text-accent: #8C9EFF;
--color-text-white-overlay: rgba(255, 255, 255, 0.6); /* White at 60% for dark backgrounds */
```

### Background
```css
--color-background: #F5F4F6;
```

### Gradients
```css
--gradient-navy-to-navy2: linear-gradient(#2A2660, #474195);
--gradient-navy2-to-navy3: linear-gradient(#474195, #554FB0);
--gradient-navy3-to-navy4: linear-gradient(#554FB0, #635CCA);
--gradient-navy3-to-accent: linear-gradient(#554FB0, #8C9EFF);
```

### Shadows
```css
--shadow-default: rgba(38, 50, 56, 0.32); /* #263238 at 32% */
```

## Typography

### Font Setup
```css
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;800&display=swap');

--font-family: 'Montserrat', sans-serif;
--font-weight-regular: 400;
--font-weight-extrabold: 800;
```

### Breakpoints
```css
--breakpoint-mobile: 991px; /* Mobile styles apply at ≤991px */
```

### Text Styles

#### H1 - Main Headline
```css
.h1, h1 {
  font-family: var(--font-family);
  font-weight: 800;
  font-size: 56px;
  line-height: 1.1; /* 110% */
  text-transform: capitalize;
}

@media (max-width: 991px) {
  .h1, h1 {
    font-size: 40px;
  }
}
```

#### H2 - Secondary Headline
```css
.h2, h2 {
  font-family: var(--font-family);
  font-weight: 800;
  font-size: 32px;
  line-height: 1.2; /* 120% */
}

@media (max-width: 991px) {
  .h2, h2 {
    font-size: 24px;
  }
}
```

#### H3 - Tertiary Headline
```css
.h3, h3 {
  font-family: var(--font-family);
  font-weight: 800;
  font-size: 16px;
  line-height: 1.2; /* 120% */
}
```

#### H4 - Small Headline (Single Line)
```css
.h4, h4 {
  font-family: var(--font-family);
  font-weight: 800;
  font-size: 14px;
  line-height: 1; /* 100% */
  text-transform: uppercase;
}
```

#### Body Text - Paragraph
```css
.paragraph, p {
  font-family: var(--font-family);
  font-weight: 400;
  font-size: 16px;
  line-height: 1.5; /* 150% */
}
```

#### Caption Text
```css
.caption {
  font-family: var(--font-family);
  font-weight: 400;
  font-size: 14px;
  line-height: 1.45; /* 145% */
}
```

#### Button Text
```css
.button, button {
  font-family: var(--font-family);
  font-weight: 800;
  font-size: 12px;
  line-height: 1.15; /* 115% */
  text-transform: uppercase;
}
```

### Price Display Styles

#### Regular Price (RRP with Strikethrough)
```css
.price-rrp {
  font-family: var(--font-family);
  font-weight: 400;
  font-size: 16px;
  line-height: 1;
  color: #B0B0B5;
  text-transform: uppercase;
  text-decoration: line-through;
  margin-right: 16px;
}
```

#### Sale Price
```css
.price-sale {
  font-family: var(--font-family);
  font-weight: 800;
  font-size: 16px;
  line-height: 1;
  color: #8C9EFF;
  text-transform: uppercase;
}
```

## Implementation Notes

### Important Rules

1. **Color Inheritance**: Text color should be inherited from parent elements EXCEPT for price styles which have explicit colors.

2. **Font Loading**: Ensure Montserrat is loaded with both weights (400 and 800) for proper rendering.

3. **Mobile First**: Consider mobile breakpoint at 991px for responsive design.

4. **Capitalization**: 
   - H1: Capitalize each word
   - H4, Buttons, Prices: ALL CAPS
   - Other elements: Normal case

### Complete CSS Variables Setup
```css
:root {
  /* Colors */
  --color-navy: #2A2660;
  --color-navy-2: #474195;
  --color-navy-3: #554FB0;
  --color-navy-4: #635CCA;
  --color-navy-accent: #8C9EFF;
  --color-accent-1: #FFCD83;
  --color-accent-2: #FF5252;
  --color-text-body: #707074;
  --color-text-body-light: #B0B0B5;
  --color-background: #F5F4F6;
  
  /* Typography */
  --font-family: 'Montserrat', sans-serif;
  --font-weight-regular: 400;
  --font-weight-extrabold: 800;
  
  /* Shadows */
  --shadow-default: 0 2px 4px rgba(38, 50, 56, 0.32);
}
```

### Usage Examples

```html
<!-- Headline with body text -->
<h1>Product Title Here</h1>
<p>Product description with regular body text styling.</p>

<!-- Price display -->
<div class="price-container">
  <span class="price-rrp">$199.00</span>
  <span class="price-sale">$149.00</span>
</div>

<!-- Button -->
<button class="button">Add to Cart</button>

<!-- Caption -->
<p class="caption">Free shipping on orders over $100</p>
```