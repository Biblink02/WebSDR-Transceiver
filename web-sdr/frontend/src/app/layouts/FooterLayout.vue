<script setup lang="ts">
// Pas de logique supplémentaire nécessaire
</script>

<template>
  <footer class="footer">
    <div class="footer__container">
      <div class="footer__layout">
        <!-- Left section: Project name and description -->
        <div class="footer__left">
          <h2 class="footer__title">
            SatCom Project
          </h2>
          <p class="footer__description">
            Developed by <span class="footer__team">PRI05</span>
          </p>
        </div>

        <!-- Center section: Navigation links -->
        <div class="footer__nav">
          <router-link
            v-for="item in ['Home', 'SDR', 'About', 'Resources']"
            :key="item"
            :to="item === 'Home' ? '/' : `/${item.toLowerCase()}`"
            class="footer__link"
          >
            {{ item }}
          </router-link>
        </div>

        <!-- Right section: Copyright and legal notice -->
        <div class="footer__right">
          <p class="footer__copyright">
            © {{ new Date().getFullYear() }} PRI05
          </p>
          <router-link
            to="/legal-notice"
            class="footer__legal-link"
          >
            Legal Notice
          </router-link>
        </div>
      </div>
    </div>
  </footer>
</template>

<style>
.footer {
  margin-top: 3rem;
  padding: 2rem 0;
  width: 100%;
  border-top: 1px solid #e5e7eb;
}

.footer__container {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

.footer__layout {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: center;
  gap: 1.5rem;
}

.footer__left {
  text-align: center;
}

.footer__title {
  font-family: monospace;
  font-size: 1.25rem;
  font-weight: bold;
  text-transform: uppercase;
  color: #1f2937;
}

.footer__description {
  font-family: monospace;
  font-size: 0.875rem;
  text-transform: uppercase;
  color: #6b7280;
  margin-top: 0.25rem;
}

.footer__team {
  font-weight: 600;
}

.footer__nav {
  display: flex;
  gap: 1.5rem;
}

.footer__link {
  font-family: monospace;
  font-size: 0.875rem;
  text-transform: uppercase;
  color: #6b7280;
  text-decoration: none;
  transition: color 0.15s ease-out;
}

.footer__link:hover {
  color: #1f2937;
}

.footer__right {
  text-align: center;
}

.footer__copyright {
  font-family: monospace;
  font-size: 0.875rem;
  text-transform: uppercase;
  color: #9ca3af;
  margin: 0;
}

.footer__legal-link {
  font-family: monospace;
  font-size: 0.75rem;
  text-transform: uppercase;
  color: #9ca3af;
  text-decoration: none;
  transition: color 0.15s ease-out;
  margin-top: 0.25rem;
  display: block;
}

.footer__legal-link:hover {
  color: #1f2937;
  text-decoration: underline;
}

@media (min-width: 768px) {
  .footer__layout {
    flex-direction: row;
  }

  .footer__left {
    text-align: left;
  }

  .footer__right {
    text-align: right;
  }
}
</style>






