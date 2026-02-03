import { describe, it, expect, beforeAll } from "vitest";
import bcrypt from "bcryptjs";
import { prisma } from "@/lib/prisma";

describe("Authentication", () => {
  describe("Password Hashing", () => {
    it("should hash passwords using bcrypt", async () => {
      const password = "changeme";
      const hash = await bcrypt.hash(password, 10);

      expect(hash).toBeDefined();
      expect(hash).not.toBe(password);
      expect(hash.length).toBeGreaterThan(0);
    });

    it("should verify passwords correctly", async () => {
      const password = "changeme";
      const hash = await bcrypt.hash(password, 10);

      const isValid = await bcrypt.compare(password, hash);
      expect(isValid).toBe(true);
    });

    it("should reject invalid passwords", async () => {
      const password = "changeme";
      const hash = await bcrypt.hash(password, 10);

      const isValid = await bcrypt.compare("wrongpassword", hash);
      expect(isValid).toBe(false);
    });
  });

  describe("User Lookup", () => {
    beforeAll(async () => {
      // Ensure test database has the seeded admin user
      const existingUser = await prisma.user.findUnique({
        where: { email: "admin@localhost" },
      });

      if (!existingUser) {
        const passwordHash = await bcrypt.hash("changeme", 10);
        await prisma.user.create({
          data: {
            email: "admin@localhost",
            name: "Admin User",
            passwordHash,
          },
        });
      }
    });

    it("should find user by email", async () => {
      const user = await prisma.user.findUnique({
        where: { email: "admin@localhost" },
      });

      expect(user).toBeDefined();
      expect(user?.email).toBe("admin@localhost");
      expect(user?.passwordHash).toBeDefined();
    });

    it("should return null for non-existent user", async () => {
      const user = await prisma.user.findUnique({
        where: { email: "nonexistent@localhost" },
      });

      expect(user).toBeNull();
    });

    it("should verify admin user password", async () => {
      const user = await prisma.user.findUnique({
        where: { email: "admin@localhost" },
      });

      expect(user).toBeDefined();

      if (user) {
        const isValid = await bcrypt.compare("changeme", user.passwordHash);
        expect(isValid).toBe(true);
      }
    });
  });
});
