export default function Header() {
  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">LinkedIn Post Generator</h2>
        <button className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition">Account</button>
      </div>
    </header>
  );
}
