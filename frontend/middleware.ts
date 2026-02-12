import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";

export default auth((req) => {
  const { pathname } = req.nextUrl;
  const isAuthenticated = !!req.auth;

  // Public routes that don't require authentication
  const publicRoutes = ["/login", "/api/auth"];
  const isPublicRoute = publicRoutes.some((route) => pathname.startsWith(route));

  // Public static assets
  const isPublicAsset = pathname.startsWith("/_next") ||
                        pathname.startsWith("/favicon.ico") ||
                        pathname.startsWith("/public") ||
                        pathname === "/manifest.json";

  if (isPublicRoute || isPublicAsset) {
    return NextResponse.next();
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    const loginUrl = new URL("/login", req.url);
    loginUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
});

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|public).*)"],
};
