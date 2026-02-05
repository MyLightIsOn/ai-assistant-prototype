-- CreateTable
CREATE TABLE "DigestSettings" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "dailyEnabled" BOOLEAN NOT NULL DEFAULT true,
    "dailyTime" TEXT NOT NULL DEFAULT '20:00',
    "weeklyEnabled" BOOLEAN NOT NULL DEFAULT true,
    "weeklyDay" TEXT NOT NULL DEFAULT 'monday',
    "weeklyTime" TEXT NOT NULL DEFAULT '09:00',
    "recipientEmail" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);
