import { test, expect } from "@playwright/test";

test.describe("Public pages (no auth required)", () => {
  test("landing page loads with hero and CTA", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("h2")).toContainText("Analisis tactico con IA");
    await expect(page.getByRole("link", { name: "Registrarse" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Empezar gratis" })).toBeVisible();
  });

  test("landing has features section", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Todo lo que tu cuerpo tecnico necesita")).toBeVisible();
    await expect(page.getByText("Analisis de video con IA")).toBeVisible();
    await expect(page.getByText("Metricas avanzadas")).toBeVisible();
    await expect(page.getByText("Informes profesionales")).toBeVisible();
  });

  test("login page loads", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
    await expect(page.getByPlaceholder("entrenador@miclub.es")).toBeVisible();
    await expect(page.getByRole("button", { name: "Entrar" })).toBeVisible();
  });

  test("login page has links to signup and forgot password", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("link", { name: "Registrate" })).toBeVisible();
    await expect(page.getByText("Has olvidado tu contrasena?")).toBeVisible();
  });

  test("signup page loads", async ({ page }) => {
    await page.goto("/signup");
    await expect(page.getByRole("heading", { name: "Registro" })).toBeVisible();
    await expect(page.getByPlaceholder("SD Huesca")).toBeVisible();
    await expect(page.getByPlaceholder("Juan Garcia")).toBeVisible();
    await expect(page.getByRole("button", { name: "Crear cuenta" })).toBeVisible();
  });

  test("pricing page loads with 3 plans", async ({ page }) => {
    await page.goto("/pricing");
    await expect(page.getByText("Planes RFAF Analytics")).toBeVisible();
    await expect(page.getByText("Basico")).toBeVisible();
    await expect(page.getByText("Profesional")).toBeVisible();
    await expect(page.getByText("Federado")).toBeVisible();
    await expect(page.getByText("49")).toBeVisible();
    await expect(page.getByText("149")).toBeVisible();
    await expect(page.getByText("104")).toBeVisible();
  });

  test("forgot password page loads", async ({ page }) => {
    await page.goto("/forgot-password");
    await expect(page.getByText("Recuperar contrasena")).toBeVisible();
    await expect(page.getByRole("button", { name: "Enviar enlace" })).toBeVisible();
  });

  test("404 page for unknown routes", async ({ page }) => {
    await page.goto("/this-page-does-not-exist");
    await expect(page.getByText("404")).toBeVisible();
    await expect(page.getByText("Pagina no encontrada")).toBeVisible();
  });
});
