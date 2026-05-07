/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{js,jsx}', './components/**/*.{js,jsx}'],
  theme: { extend: { colors: { brand: { blue: '#2563EB', green: '#16A34A' } } } },
  plugins: []
};
