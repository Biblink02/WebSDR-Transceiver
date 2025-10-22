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
  margin-top: 4rem;
  padding: 3rem 0;
  width: 100%;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  background-color: rgba(0, 0, 0, 0.3);
  backdrop-filter: transparent;
}

.footer__container {
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 2rem;
}

.footer__layout {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: center;
  gap: 2rem;
}

.footer__left {
  text-align: center;
}

.footer__title {
  font-family: monospace;
  font-size: 1.5rem;
  font-weight: bold;
  text-transform: uppercase;
  color: #ffffff;
  letter-spacing: 2px;
  margin: 0;
}

.footer__description {
  font-family: monospace;
  font-size: 0.95rem;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.8);
  margin-top: 0.5rem;
  letter-spacing: 1px;
}

.footer__team {
  font-weight: 600;
  color: #ffffff;
}

.footer__nav {
  display: flex;
  gap: 2.5rem;
}

.footer__link {
  font-family: monospace;
  font-size: 1rem;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  transition: color 0.2s ease-out;
  letter-spacing: 1px;
}

.footer__link:hover {
  color: #ffffff;
  text-decoration: underline;
}

.footer__right {
  text-align: center;
}

.footer__copyright {
  font-family: monospace;
  font-size: 0.9rem;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.7);
  margin: 0;
  letter-spacing: 1px;
}

.footer__legal-link {
  font-family: monospace;
  font-size: 0.85rem;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  transition: color 0.2s ease-out;
  margin-top: 0.5rem;
  display: inline-block;
  letter-spacing: 1px;
}

.footer__legal-link:hover {
  color: #ffffff;
  text-decoration: underline;
}

@media (min-width: 768px) {
  .footer__layout {
    flex-direction: row;
    align-items: center;
  }

  .footer__left {
    text-align: left;
    flex: 1;
  }

  .footer__nav {
    flex: 1;
    justify-content: center;
  }

  .footer__right {
    text-align: right;
    flex: 1;
  }
}
</style>






