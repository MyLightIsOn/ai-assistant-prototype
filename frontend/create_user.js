const bcrypt = require('bcryptjs');
const { PrismaClient } = require('@prisma/client');

const prisma = new PrismaClient();

async function createUser() {
  try {
    // First, delete the existing user
    await prisma.user.deleteMany({
      where: { email: 'thelawrencemoore@gmail.com' }
    });
    console.log('Deleted existing user');

    // Create new user with proper Prisma format
    const passwordHash = await bcrypt.hash('Test123!', 12);

    const user = await prisma.user.create({
      data: {
        email: 'thelawrencemoore@gmail.com',
        name: 'Lawrence Moore',
        passwordHash: passwordHash
      }
    });

    console.log('✅ User created:', user.email);
    console.log('   ID:', user.id);
    console.log('   Name:', user.name);
    console.log('   Password: Test123!');

    // Verify login works
    const testUser = await prisma.user.findUnique({
      where: { email: 'thelawrencemoore@gmail.com' }
    });

    if (testUser) {
      const isValid = await bcrypt.compare('Test123!', testUser.passwordHash);
      console.log('   Login test:', isValid ? '✅ PASS' : '❌ FAIL');
    }

  } catch (error) {
    console.error('❌ Error:', error.message);
  } finally {
    await prisma.$disconnect();
  }
}

createUser();
