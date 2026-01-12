document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const navbar = document.getElementById('navbar');
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');
    const cartBtn = document.getElementById('cart-btn');
    const cartDrawer = document.getElementById('cart-drawer');
    const closeCartBtn = document.getElementById('close-cart');
    const overlay = document.getElementById('overlay');

    // Sticky Navbar Logic
    if (navbar) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                navbar.classList.add('shadow-md', 'py-2');
                navbar.classList.remove('py-4');
            } else {
                navbar.classList.remove('shadow-md', 'py-2');
                navbar.classList.add('py-4');
            }
        });
    }

    // Mobile Menu Toggle
    if (mobileMenuBtn && mobileMenu) {
        mobileMenuBtn.addEventListener('click', () => {
            mobileMenu.classList.toggle('hidden');
        });
    }

    // Cart Drawer Logic
    function openCart() {
        if (cartDrawer && overlay) {
            cartDrawer.classList.remove('translate-x-full');
            overlay.classList.remove('hidden');
            document.body.style.overflow = 'hidden'; // Prevent background scrolling
        }
    }

    function closeCart() {
        if (cartDrawer && overlay) {
            cartDrawer.classList.add('translate-x-full');
            overlay.classList.add('hidden');
            document.body.style.overflow = '';
        }
    }

    if (cartBtn) {
        cartBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openCart();
        });
    }

    if (closeCartBtn) {
        closeCartBtn.addEventListener('click', closeCart);
    }

    if (overlay) {
        overlay.addEventListener('click', () => {
            closeCart();
            // Also close mobile menu if open
            if (mobileMenu && !mobileMenu.classList.contains('hidden')) {
                mobileMenu.classList.add('hidden');
            }
        });
    }

    // Add to Cart Animation (Simple feedback)
    const addToCartButtons = document.querySelectorAll('.add-to-cart-btn, button');
    addToCartButtons.forEach(btn => {
        // Check if it's an add to cart button (either by class or context)
        if (btn.classList.contains('add-to-cart-btn') || btn.textContent.includes('Add to Cart') || btn.textContent.includes('Add')) {
            // Avoid adding listener multiple times or to wrong buttons
            if (btn.dataset.hasListener) return;

            // Skip if it's the mobile menu button or other UI controls
            if (btn.id === 'mobile-menu-btn' || btn.id === 'cart-btn' || btn.id === 'login-btn' || btn.id === 'close-cart') return;

            btn.dataset.hasListener = 'true';
            btn.addEventListener('click', function (e) {
                // Don't prevent default if it's a link, but these are buttons

                const originalText = this.innerHTML;
                const isIconBtn = this.classList.contains('add-to-cart-btn'); // specific class check

                this.innerHTML = '<i class="fa-solid fa-check"></i> Added';

                // Toggle classes for feedback
                if (this.classList.contains('bg-white')) {
                    this.classList.remove('bg-white', 'text-fantasy-brown', 'border-fantasy-brown');
                    this.classList.add('bg-green-600', 'text-white', 'border-green-600');
                } else if (this.classList.contains('bg-fantasy-brown')) {
                    this.classList.remove('bg-fantasy-brown');
                    this.classList.add('bg-green-600');
                }

                // Update cart count badge (simulated)
                const badge = document.querySelector('#cart-btn span');
                if (badge) {
                    let count = parseInt(badge.textContent);
                    badge.textContent = count + 1;
                    badge.classList.add('scale-125');
                    setTimeout(() => badge.classList.remove('scale-125'), 200);
                }

                setTimeout(() => {
                    this.innerHTML = originalText;
                    if (this.classList.contains('bg-green-600')) {
                        this.classList.remove('bg-green-600', 'text-white', 'border-green-600');
                        if (originalText.includes('Add') && !originalText.includes('Cart')) {
                            // Small button style
                            this.classList.add('bg-white', 'text-fantasy-brown', 'border-fantasy-brown');
                        } else {
                            // Large button style
                            this.classList.add('bg-fantasy-brown', 'text-white');
                        }
                    }
                }, 2000);
            });
        }
    });

    // Wishlist Toggle
    const wishlistButtons = document.querySelectorAll('.wishlist-btn, button');
    wishlistButtons.forEach(btn => {
        if (btn.classList.contains('wishlist-btn') || btn.querySelector('.fa-heart')) {
            if (btn.dataset.hasWishlistListener) return;
            if (btn.id === 'cart-btn') return; // Skip cart button which has heart icon sometimes nearby

            btn.dataset.hasWishlistListener = 'true';
            btn.addEventListener('click', function (e) {
                // e.preventDefault(); // Optional
                const icon = this.querySelector('i');
                if (icon && icon.classList.contains('fa-heart')) {
                    if (icon.classList.contains('fa-regular')) {
                        icon.classList.remove('fa-regular');
                        icon.classList.add('fa-solid', 'text-red-500');
                    } else {
                        icon.classList.remove('fa-solid', 'text-red-500');
                        icon.classList.add('fa-regular');
                    }
                }
            });
        }
    });

    // Countdown Timer Logic (if elements exist)
    const hoursEl = document.getElementById('hours');
    const minutesEl = document.getElementById('minutes');
    const secondsEl = document.getElementById('seconds');

    if (hoursEl && minutesEl && secondsEl) {
        let duration = 12 * 60 * 60; // 12 hours in seconds
        setInterval(() => {
            duration--;
            if (duration < 0) duration = 12 * 60 * 60;

            const h = Math.floor(duration / 3600);
            const m = Math.floor((duration % 3600) / 60);
            const s = duration % 60;

            hoursEl.textContent = h.toString().padStart(2, '0');
            minutesEl.textContent = m.toString().padStart(2, '0');
            secondsEl.textContent = s.toString().padStart(2, '0');
        }, 1000);
    }
});

// Global function for Copy Code
window.copyCode = function (code) {
    navigator.clipboard.writeText(code).then(() => {
        alert('Code ' + code + ' copied to clipboard! 🪄');
    }).catch(err => {
        console.error('Failed to copy: ', err);
    });
};

// Login Page Logic
document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const passwordInput = document.getElementById('password');
    const togglePasswordBtn = document.getElementById('toggle-password');
    const emailInput = document.getElementById('email');

    // Password Toggle (Instagram Style: Show/Hide text)
    if (togglePasswordBtn && passwordInput) {
        // Show button only when there is text
        passwordInput.addEventListener('input', () => {
            if (passwordInput.value.length > 0) {
                togglePasswordBtn.classList.remove('hidden');
            } else {
                togglePasswordBtn.classList.add('hidden');
            }
        });

        togglePasswordBtn.addEventListener('click', () => {
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);

            // Toggle text
            if (type === 'text') {
                togglePasswordBtn.textContent = 'Hide';
            } else {
                togglePasswordBtn.textContent = 'Show';
            }
        });
    }

    // Form Submission
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();

            let isValid = true;

            // Simple Validation
            if (!emailInput.value) {
                isValid = false;
                emailInput.classList.add('border-red-500');
                setTimeout(() => {
                    emailInput.classList.remove('border-red-500');
                }, 1000);
            }

            if (!passwordInput.value) {
                isValid = false;
                passwordInput.classList.add('border-red-500');
                setTimeout(() => {
                    passwordInput.classList.remove('border-red-500');
                }, 1000);
            }

            if (isValid) {
                const submitBtn = document.getElementById('login-submit-btn');
                const originalContent = submitBtn.innerHTML;

                // Loading State
                submitBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Logging in...';
                submitBtn.disabled = true;
                submitBtn.classList.add('opacity-70', 'cursor-not-allowed');

                // Simulate API call
                setTimeout(() => {
                    // Success
                    submitBtn.innerHTML = '<i class="fa-solid fa-check"></i> Success';
                    submitBtn.classList.remove('bg-kerala-green');
                    submitBtn.classList.add('bg-green-600');

                    setTimeout(() => {
                        window.location.href = 'index.html';
                    }, 1000);
                }, 1500);
            }
        });
    }
});
