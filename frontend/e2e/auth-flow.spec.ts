import { test, expect } from "@playwright/test";

test.describe("Authentication flow", () => {
  test("protected routes redirect to login", async ({ page }) => {
    // Clear any cookies
    await page.context().clearCookies();

    await page.goto("/analyze");
    await page.waitForURL("**/login**");
    expect(page.url()).toContain("/login");
  });

  test("reports page redirects to login when not authenticated", async ({ page }) => {
    await page.context().clearCookies();
    await page.goto("/reports");
    await page.waitForURL("**/login**");
    expect(page.url()).toContain("/login");
  });

  test("settings page redirects to login when not authenticated", async ({ page }) => {
    await page.context().clearCookies();
    await page.goto("/settings");
    await page.waitForURL("**/login**");
    expect(page.url()).toContain("/login");
  });

  test("login form shows error on invalid credentials", async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[type="email"]', "fake@test.com");
    await page.fill('input[type="password"]', "wrongpassword");
    await page.click('button[type="submit"]');

    // Should show error (backend may not be running, so we check for either
    // auth error or connection error)
    await expect(
      page.locator(".bg-red-50").or(page.getByText("Error"))
    ).toBeVisible({ timeout: 10_000 });
  });

  test("signup form validates password length", async ({ page }) => {
    await page.goto("/signup");
    await page.fill('input[placeholder="SD Huesca"]', "Test Club");
    await page.fill('input[placeholder="Juan Garcia"]', "Test User");
    await page.fill('input[type="email"]', "test@test.com");
    await page.fill('input[type="password"]', "short");
    await page.click('button[type="submit"]');

    await expect(page.getByText("al menos 8 caracteres")).toBeVisible();
  });

  test("navigation between login and signup", async ({ page }) => {
    await page.goto("/login");
    await page.click('a[href="/signup"]');
    await page.waitForURL("**/signup");
    await expect(page.getByRole("heading", { name: "Registro" })).toBeVisible();

    await page.click('a[href="/login"]');
    await page.waitForURL("**/login");
    await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
  });
});
