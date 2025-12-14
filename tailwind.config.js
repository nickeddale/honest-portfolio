/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/static/**/*.html",
    "./app/static/js/**/*.js"
  ],
  theme: {
    extend: {
      fontFamily: {
        head: ['Archivo Black', 'sans-serif'],
        sans: ['Space Grotesk', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

