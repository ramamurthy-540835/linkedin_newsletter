import { NextResponse } from 'next/server';

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const code = searchParams.get('code');
  const target = code ? '/publish?auth=success' : '/publish?auth=error';
  return NextResponse.redirect(new URL(target, request.url));
}
