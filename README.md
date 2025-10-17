# 🩺 MediKate — Health & Personal Care E-Commerce Platform

MediKate is a **Django-based e-commerce web application** focused on selling **health-related and personal care products**.  
It provides an intuitive shopping experience with secure authentication, online payment integration, and user-friendly UI.

> ⚙️ **Note:** This project is currently under active development and not yet fully completed.

---

## 🚀 Features

- 🛍️ **Product Management** – Browse, search, and manage health and personal care products  
- 👤 **User Authentication** – Custom user model with email verification and Google login (via `django-allauth`)  
- 💳 **Payment Gateway** – Razorpay integration for secure payments  
- ✉️ **Email Verification** – OTP-based email confirmation using Django’s email backend  
- 🧾 **Order & Checkout System** – End-to-end checkout flow with address and order handling  
- 📦 **Cart System** – Add, update, and manage items in your shopping cart  
- 🗃️ **PostgreSQL Database** – Reliable and scalable database integration  
- 📸 **Image Handling** – Product image uploads and processing with `django-imagekit`  
- 🎨 **Responsive UI** – Built with HTML, CSS, and Bootstrap 5  

---

## 🧩 Tech Stack

**Backend:** Python, Django, Django ORM  
**Frontend:** HTML, CSS, Bootstrap  
**Database:** PostgreSQL  
**Authentication:** Django-Allauth (Google Auth)  
**Payments:** Razorpay API  
**Email Service:** Gmail SMTP (for OTP verification)  

---

## 📦 Dependencies

Below are the main dependencies used in MediKate:

asgiref==3.8.1
certifi==2025.6.15
cffi==1.17.1
charset-normalizer==3.4.2
cryptography==45.0.5
Django==5.2.1
django-allauth==65.9.0
django-appconf==1.1.0
django-imagekit==5.0.0
idna==3.10
numpy==1.26.4
pilkit==3.0
pillow==11.2.1
psycopg2==2.9.10
pycparser==2.22
PyJWT==2.10.1
python-decouple==3.8
razorpay==1.4.2
requests==2.32.4
setuptools==80.9.0
sqlparse==0.5.3
tzdata==2025.2
urllib3==2.5.0

