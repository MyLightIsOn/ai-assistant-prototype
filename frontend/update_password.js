const bcrypt = require('bcryptjs');
const { PrismaClient } = require('@prisma/client');

const prisma = new PrismaClient();

async function updatePassword() {
  try {
    const newPassword = 'Test123!';
    const passwordHash = await bcrypt.hash(newPassword, 12);

    const user = await prisma.user.update({
      where: { email: 'thelawrencemoore@gmail.com' },
      data: { passwordHash }
    });

    console.log('✅ Password updated for:', user.email);
    console.log('   New password:', newPassword);
    console.log('   Hash:', passwordHash.substring(0, 30) + '...');

    // Test the password
    const isValid = await bcrypt.compare(newPassword, passwordHash);
    console.log('   Verification test:', isValid ? '✅ PASS' : '❌ FAIL');

  } catch (error) {
    console.error('❌ Error:', error.message);
  } finally {
    await prisma.$disconnect();
  }
}

updatePassword();
