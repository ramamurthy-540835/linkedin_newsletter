export default function Card({ children, className = '', title, subtitle }) {
  return (
    <div className={`rounded-2xl shadow-card hover:shadow-card-hover transition-shadow duration-200 border border-gray-100 bg-white p-5 ${className}`}>
      {(title || subtitle) && (
        <div className="mb-4">
          {title && <h3 className="text-base font-semibold text-gray-900 mb-0.5">{title}</h3>}
          {subtitle && <p className="text-sm text-gray-500">{subtitle}</p>}
        </div>
      )}
      {children}
    </div>
  );
}
