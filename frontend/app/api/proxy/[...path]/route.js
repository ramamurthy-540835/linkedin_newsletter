import { NextResponse } from 'next/server';

const BACKEND = process.env.INTERNAL_API_URL || 'http://127.0.0.1:8007';

async function forward(request, params) {
  const path = (params?.path || []).join('/');
  const url = new URL(`${BACKEND}/${path}`);
  url.search = new URL(request.url).search;

  const headers = new Headers(request.headers);
  headers.delete('host');

  const init = {
    method: request.method,
    headers,
    body: request.method === 'GET' || request.method === 'HEAD' ? undefined : await request.text(),
    cache: 'no-store',
  };

  try {
    const res = await fetch(url.toString(), init);
    const text = await res.text();
    return new NextResponse(text, {
      status: res.status,
      headers: {
        'content-type': res.headers.get('content-type') || 'application/json',
        'cache-control': 'no-store',
      },
    });
  } catch (error) {
    return NextResponse.json(
      {
        detail: `Proxy upstream fetch failed: ${error?.message || 'unknown error'}`,
        upstream: url.toString(),
      },
      { status: 502 }
    );
  }
}

export async function GET(request, { params }) { return forward(request, params); }
export async function POST(request, { params }) { return forward(request, params); }
export async function PUT(request, { params }) { return forward(request, params); }
export async function PATCH(request, { params }) { return forward(request, params); }
export async function DELETE(request, { params }) { return forward(request, params); }
