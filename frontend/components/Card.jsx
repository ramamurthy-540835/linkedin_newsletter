export default function Card({ children, className='' }) { return <div className={`bg-white border rounded-lg p-4 ${className}`}>{children}</div>; }
