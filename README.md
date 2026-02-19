<p align="center">
  <h1 align="center">🩺 MediKate — Health & Personal Care E-Commerce Platform</h1>
  <p align="center">
    A full-featured Django-based e-commerce platform for health, wellness and personal care products.<br>
    Built with a modern tech stack, secure payments, and a powerful admin dashboard.
  </p>
  <p align="center">
    <a href="https://medikate.xyz">🌐 Live Demo</a> •
    <a href="#-features">Features</a> •
    <a href="#-tech-stack">Tech Stack</a> •
    <a href="#-getting-started">Getting Started</a>
  </p>
</p>

---

## 📸 Live Preview

🔗 **[medikate.xyz](https://medikate.xyz)**  

---

## ✨ Features

### 🛍️ Customer-Facing
| Feature | Description |
|---|---|
| **Product Browsing** | Browse products by categories, search, sort, and filter with pagination |
| **Product Variants** | Multiple variants per product (size, quantity) with individual pricing and stock |
| **Product Offers** | Product-level and category-level discount offers with automatic best-price calculation |
| **Shopping Cart** | Add, update quantity, and remove items with real-time price calculation |
| **Wishlist** | Save products for later with one-click add-to-cart |
| **Checkout Flow** | Multi-step checkout with address selection, coupon application, and payment method |
| **Buy Now** | Quick single-item purchase flow bypassing the cart |
| **Multiple Payment Methods** | Cash on Delivery (COD), Razorpay online payment, and Wallet payment |
| **Order Tracking** | Real-time order status tracking (Pending → Processing → Shipped → Delivered) |
| **Order Cancellation** | Cancel individual items with reason selection and automatic refund to wallet |
| **Return & Refund** | Request returns with admin approval workflow and wallet refund |
| **Invoice Download** | Download PDF invoices for completed orders |
| **Digital Wallet** | In-app wallet with credit/debit transaction history |
| **Coupon System** | Apply discount coupons at checkout with validation (min purchase, usage limits, expiry) |
| **Referral Program** | Unique referral codes with ₹100 reward for both referrer and referee |
| **User Profile** | Manage profile details, multiple delivery addresses (up to 5), and email verification |
| **Image Zoom** | Product image zoom on hover for detailed viewing |

### 🔐 Authentication & Security
| Feature | Description |
|---|---|
| **Email/Password Login** | Custom user model with email-based authentication |
| **Google OAuth** | One-click Google sign-in via `django-allauth` |
| **OTP Verification** | Email OTP verification for registration and password reset |
| **Forgot Password** | Secure password reset flow via email OTP |
| **User Blocking** | Admin can block/unblock users with auto-logout middleware |
| **Production Security** | HSTS, SSL redirect, secure cookies, XSS/CSRF protection |

### 📊 Admin Dashboard
| Feature | Description |
|---|---|
| **Dashboard Overview** | Key metrics — total revenue, orders, users, and top-selling products |
| **Sales Charts** | Interactive sales analytics with filterable date ranges |
| **User Management** | View, create, block/unblock users and view their wallet transactions |
| **Product Management** | Full CRUD for products, variants, images, and categories |
| **Order Management** | View all orders, update delivery statuses, manage returns |
| **Return Approval** | Review and approve/deny return requests with automatic refund processing |
| **Coupon Management** | Create, edit, delete, and toggle discount coupons |
| **Offer Management** | Create product-level and category-level percentage discount offers |
| **Sales Reports** | Generate sales reports by date range with PDF export |
| **Wallet Overview** | View all user wallets and transaction histories |

---

## 🧩 Tech Stack

### Core
| Technology | Purpose |
|---|---|
| **Python 3.12** | Backend programming language |
| **Django 5.2** | Web framework |
| **PostgreSQL** | Primary relational database |
| **HTML5 / CSS3 / JavaScript** | Frontend structure, styling, and interactivity |
| **Bootstrap 5** | Responsive UI framework |

### Infrastructure & Deployment
| Technology | Purpose |
|---|---|
| **AWS EC2** | Cloud hosting (Ubuntu 24.04 LTS) |
| **Gunicorn** | WSGI HTTP server for production |
| **Nginx** | Reverse proxy and static file serving |
| **WhiteNoise** | Static file serving in production |
| **Cloudinary** | Cloud-based media/image storage and CDN |

### APIs & Integrations
| Service | Purpose |
|---|---|
| **Razorpay API** | Online payment gateway for secure transactions |
| **Google OAuth 2.0** | Social authentication via Google accounts |
| **Gmail SMTP** | Transactional emails — OTP verification, password reset |
| **Cloudinary API** | Media file upload, storage, and transformation |

---

## 📦 Key Dependencies

| Package | Version | Purpose |
|---|---|---|
| `Django` | 5.2.1 | Web framework |
| `psycopg2` | 2.9.10 | PostgreSQL database adapter |
| `django-allauth` | 65.9.0 | Authentication — Google OAuth & email verification |
| `razorpay` | 1.4.2 | Razorpay payment gateway SDK |
| `cloudinary` | 1.44.1 | Cloudinary Python SDK |
| `django-cloudinary-storage` | 0.3.0 | Django storage backend for Cloudinary |
| `whitenoise` | 6.11.0 | Static file serving for production |
| `django-imagekit` | 5.0.0 | Image processing and thumbnail generation |
| `Pillow` | 11.2.1 | Python imaging library |
| `xhtml2pdf` | 0.2.17 | HTML to PDF conversion (invoices & reports) |
| `reportlab` | 4.4.9 | PDF generation engine |
| `python-decouple` | 3.8 | Environment variable management |
| `PyJWT` | 2.10.1 | JSON Web Token handling |
| `pyngrok` | 7.4.0 | Ngrok tunnel for development/testing |

---

## 🏗️ Project Architecture

```
medatecom/                      # Django Project Root
│
├── medatecom/                  # Project Configuration
│   ├── settings.py             # Django settings (DB, Auth, Cloudinary, etc.)
│   ├── urls.py                 # Root URL configuration
│   └── wsgi.py                 # WSGI entry point
│
├── ecomauth/                   # Authentication App
│   ├── views.py                # Login, Register, OTP, Google Auth, Password Reset
│   └── middlwares.py           # Blocked user auto-logout middleware
│
├── ecomproducts/               # Product Management App
│   ├── models.py               # Product, ProductVariant, Categories, Coupon, Offer, ProductImage
│   └── views.py                # Product listing, details, search, filtering
│
├── ecomusers/                  # User Management App
│   ├── models.py               # User, UserAddress, CartProducts, WishlistProducts,
│   │                           #   Wallet, WalletTransaction, Referral
│   └── views.py                # Profile, Cart, Wishlist, Wallet, Address management
│
├── ecomorders/                 # Order Management App
│   ├── models.py               # Order, OrderItem, ReturnRequest
│   ├── views.py                # Checkout, Payment, Order tracking, Cancellation, Returns
│   └── utils.py                # PDF rendering utilities
│
├── ecomadmin/                  # Admin Dashboard App
│   └── views.py                # Dashboard, CRUD operations, Sales reports, Analytics
│
├── templates/                  # HTML Templates
│   ├── auth/                   # Login, Register, OTP, Password reset pages
│   ├── admin/                  # Admin dashboard and management pages
│   ├── user/                   # Customer-facing pages (cart, checkout, orders, profile)
│   └── extra/                  # Shared components (breadcrumbs, toast notifications, zoom)
│
├── static/                     # Static Assets (CSS, JS, Images)
├── media/                      # User-uploaded media (managed via Cloudinary)
├── requirements.txt            # Python dependencies
└── manage.py                   # Django management script
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- PostgreSQL 15+
- Git

### Installation

**1. Clone the repository**
```bash
git clone https://github.com/abdullathaj/medikate-ecommerce.git
cd medikate-ecommerce
```

**2. Create and activate a virtual environment**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r medatecom/requirements.txt
```

**4. Set up the `.env` file**

Create a `.env` file inside the `medatecom/` directory:

```env
# SECURITY
SECRET_KEY=your-django-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1

# DATABASE
DB_NAME=medat_database
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

# CLOUDINARY
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# RAZORPAY
RAZORPAY_KEY_ID=your-razorpay-key
RAZORPAY_KEY_SECRET=your-razorpay-secret

# EMAIL (Gmail SMTP)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# GOOGLE OAUTH
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

**5. Create the database**
```bash
# In PostgreSQL
CREATE DATABASE medat_database;
```

**6. Run migrations**
```bash
cd medatecom
python manage.py migrate
```

**7. Create a superuser**
```bash
python manage.py createsuperuser
```

**8. Run the development server**
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000` to access the application.

---

## 🌐 Deployment

The application is deployed on **AWS EC2** with the following stack:

- **Ubuntu 24.04 LTS** — Operating system
- **Gunicorn** — WSGI application server
- **Nginx** — Reverse proxy server
- **PostgreSQL** — Production database
- **Cloudinary** — Media file CDN
- **WhiteNoise** — Static file compression and caching
- **Custom Domain** — [medikate.xyz](https://medikate.xyz) with SSL

---

## 📄 License

This project is developed as part of the **Brocamp Full-Stack Development Program**.

---

<p align="center">
  Made with ❤️ by <strong>Abdulla Thaj</strong>
</p>
