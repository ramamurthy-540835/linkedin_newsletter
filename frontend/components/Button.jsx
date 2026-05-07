import Link from 'next/link';
const v={primary:'bg-blue-600 text-white',secondary:'bg-gray-200 text-gray-900',danger:'bg-red-600 text-white',tertiary:'bg-white border text-gray-900'};
const s={sm:'px-3 py-1 text-sm',md:'px-4 py-2',lg:'px-5 py-3'};
export default function Button({href,onClick,variant='primary',size='md',disabled,children,className=''}){const c=`inline-flex items-center justify-center rounded ${v[variant]} ${s[size]} ${disabled?'opacity-60 cursor-not-allowed':''} ${className}`;return href?<Link href={href} className={c}>{children}</Link>:<button onClick={onClick} disabled={disabled} className={c}>{children}</button>;}
