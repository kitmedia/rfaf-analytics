import { test, expect } from "@playwright/test";

test.describe("Navigation and UI elements", () => {
  test("landing page navbar has correct links", async ({ page }) => {
    await page.goto("/");
    const nav = page.locator("nav");
    await expect(nav.getByText("RFAF Analytics")).toBeVisible();
    await expect(nav.getByRole("link", { name: "Precios" })).toHaveAttribute("href", "/pricing");
    await expect(nav.getByRole("link", { name: "Entrar" })).toHaveAttribute("href", "/login");
    await expect(nav.getByRole("link", { name: "Registrarse" })).toHaveAttribute("href", "/signup");
  });

  test("pricing page CTA buttons exist for each plan", async ({ page }) => {
    await page.goto("/pricing");
    await expect(page.getByRole("button", { name: "Empezar" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Suscribirse" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Solicitar acceso" })).toBeVisible();
  });

  test("landing footer shows version and RFAF", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("RFAF Analytics Platform v2.0")).toBeVisible();
    await expect(page.getByText("Real Federacion Aragonesa de Futbol")).toBeVisible();
  });

  test("reset-password page loads with token param", async ({ page }) => {
    await page.goto("/reset-password?token=test123");
    await expect(page.getByText("Nueva contrasena")).toBeVisible();
    await expect(page.getByRole("button", { name: "Guardar contrasena" })).toBeVisible();
  });

  test("reset-password validates matching passwords", async ({ page }) => {
    await page.goto("/reset-password?token=test123");
    const passwordInputs = page.locator('input[type="password"]');
    await passwordInputs.nth(0).fill("newpassword123");
    await passwordInputs.nth(1).fill("differentpassword");
    await page.click('button[type="submit"]');
    await expect(page.getByText("no coinciden")).toBeVisible();
  });
});
