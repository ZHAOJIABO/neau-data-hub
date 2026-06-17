<template>
  <div class="login-page">
    <div class="login-page__background">
      <div class="login-page__orb login-page__orb--violet"></div>
      <div class="login-page__orb login-page__orb--cyan"></div>
      <div class="login-page__grid"></div>
    </div>

    <section class="login-shell">
      <div class="login-showcase">
        <p class="login-showcase__eyebrow">WATERSMART · DATA × MODELS</p>
        <h1 class="login-showcase__title">玄冥数据与模型平台</h1>
        <p class="login-showcase__subtitle">Watershed Data & Model Platform</p>
        <p class="login-showcase__description">
          面向灌区业务场景，统一集成数据资产、专业模型、智能分析与协同应用，打通从感知采集到模型决策的全链路工作流。
        </p>

        <div class="login-showcase__highlights">
          <span>IRRIGATION DISTRICT</span>
          <span>DATA ASSETS</span>
          <span>MODEL INTEGRATION</span>
          <span>AI ANALYTICS</span>
        </div>

        <div class="login-showcase__stats">
          <div class="stat-card">
            <span class="stat-card__value">24/7</span>
            <span class="stat-card__label">Always-on Platform Services</span>
          </div>
          <div class="stat-card">
            <span class="stat-card__value">Models</span>
            <span class="stat-card__label">Hydrology · Dispatch · Forecast</span>
          </div>
          <div class="stat-card">
            <span class="stat-card__value">Secure</span>
            <span class="stat-card__label">Role-based Access & Audit Trail</span>
          </div>
        </div>
      </div>

      <div class="login-panel">
        <div class="login-panel__header">
          <div>
            <p class="login-panel__kicker">WELCOME BACK</p>
            <h2 class="login-panel__title">登录 {{ title }}</h2>
            <p class="login-panel__caption">Sign in to access data assets, domain models and operational intelligence.</p>
          </div>
          <div class="login-panel__badge">Model-Driven Portal</div>
        </div>

        <el-form ref="loginRef" :model="loginForm" :rules="loginRules" class="login-form">
          <el-form-item prop="username">
            <el-input
              v-model="loginForm.username"
              type="text"
              size="large"
              auto-complete="off"
              placeholder="Username / 请输入账号"
            >
              <template #prefix><svg-icon icon-class="user" class="el-input__icon input-icon" /></template>
            </el-input>
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              size="large"
              auto-complete="off"
              placeholder="Password / 请输入密码"
              show-password
              @keyup.enter="handleLogin"
            >
              <template #prefix><svg-icon icon-class="password" class="el-input__icon input-icon" /></template>
            </el-input>
          </el-form-item>

          <el-form-item prop="code" v-if="captchaEnabled" class="login-form__captcha-row">
            <el-input
              v-model="loginForm.code"
              size="large"
              auto-complete="off"
              placeholder="Captcha / 请输入验证码"
              @keyup.enter="handleLogin"
            >
              <template #prefix><svg-icon icon-class="validCode" class="el-input__icon input-icon" /></template>
            </el-input>
            <button type="button" class="login-captcha" @click="getCode">
              <img :src="codeUrl" alt="验证码" class="login-captcha__img" />
            </button>
          </el-form-item>

          <div class="login-form__meta">
            <el-checkbox v-model="loginForm.rememberMe">Remember me</el-checkbox>
            <router-link v-if="register" class="login-form__link" :to="'/register'">Create account</router-link>
          </div>

          <el-form-item class="login-form__action">
            <el-button :loading="loading" size="large" type="primary" class="login-form__submit" @click.prevent="handleLogin">
              <span v-if="!loading">SIGN IN</span>
              <span v-else>SIGNING IN...</span>
            </el-button>
          </el-form-item>
        </el-form>

        <p class="login-panel__footer">{{ footerContent }}</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { getCodeImg } from "@/api/login";
import Cookies from "js-cookie";
import { encrypt, decrypt } from "@/utils/jsencrypt";
import useUserStore from '@/store/modules/user'
import defaultSettings from '@/settings'

const title = import.meta.env.VITE_APP_TITLE;
const footerContent = defaultSettings.footerContent
const userStore = useUserStore();
const route = useRoute();
const router = useRouter();
const { proxy } = getCurrentInstance();

const loginForm = ref({
  username: "",
  password: "",
  rememberMe: false,
  code: "",
  uuid: ""
});

const loginRules = {
  username: [{ required: true, trigger: "blur", message: "请输入您的账号" }],
  password: [{ required: true, trigger: "blur", message: "请输入您的密码" }],
  code: [{ required: true, trigger: "change", message: "请输入验证码" }]
};

const codeUrl = ref("");
const loading = ref(false);
const captchaEnabled = ref(true);
const register = ref(false);
const redirect = ref(undefined);

watch(route, (newRoute) => {
  redirect.value = newRoute.query && newRoute.query.redirect;
}, { immediate: true });

function handleLogin() {
  proxy.$refs.loginRef.validate(valid => {
    if (valid) {
      loading.value = true;
      if (loginForm.value.rememberMe) {
        Cookies.set("username", loginForm.value.username, { expires: 30 });
        Cookies.set("password", encrypt(loginForm.value.password), { expires: 30 });
        Cookies.set("rememberMe", loginForm.value.rememberMe, { expires: 30 });
      } else {
        Cookies.remove("username");
        Cookies.remove("password");
        Cookies.remove("rememberMe");
      }
      userStore.login(loginForm.value).then(() => {
        const query = route.query;
        const otherQueryParams = Object.keys(query).reduce((acc, cur) => {
          if (cur !== "redirect") {
            acc[cur] = query[cur];
          }
          return acc;
        }, {});
        router.push({ path: redirect.value || "/", query: otherQueryParams });
      }).catch(() => {
        loading.value = false;
        if (captchaEnabled.value) {
          getCode();
        }
      });
    }
  });
}

function getCode() {
  getCodeImg().then(res => {
    captchaEnabled.value = res.captchaEnabled === undefined ? true : res.captchaEnabled;
    register.value = res.registerEnabled === undefined ? false : res.registerEnabled;
    if (captchaEnabled.value) {
      codeUrl.value = "data:image/gif;base64," + res.img;
      loginForm.value.uuid = res.uuid;
    }
  });
}

function getCookie() {
  const username = Cookies.get("username");
  const password = Cookies.get("password");
  const rememberMe = Cookies.get("rememberMe");
  loginForm.value = {
    username: username === undefined ? loginForm.value.username : username,
    password: password === undefined ? loginForm.value.password : decrypt(password),
    rememberMe: rememberMe === undefined ? false : Boolean(rememberMe),
    code: "",
    uuid: loginForm.value.uuid
  };
}

getCode();
getCookie();
</script>

<style lang='scss' scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  background:
    radial-gradient(circle at top left, rgba(97, 76, 255, 0.35), transparent 34%),
    radial-gradient(circle at right 20%, rgba(0, 198, 255, 0.22), transparent 28%),
    linear-gradient(135deg, #07111f 0%, #0d1a2f 38%, #121f3f 100%);
  color: #f4f7fb;
}

.login-page__background {
  position: absolute;
  inset: 0;
}

.login-page__orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(12px);
  opacity: 0.8;
}

.login-page__orb--violet {
  top: 8%;
  left: -8%;
  width: 360px;
  height: 360px;
  background: rgba(122, 92, 255, 0.38);
}

.login-page__orb--cyan {
  right: -4%;
  bottom: 10%;
  width: 280px;
  height: 280px;
  background: rgba(0, 204, 255, 0.2);
}

.login-page__grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.06) 1px, transparent 1px);
  background-size: 56px 56px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.52), transparent 92%);
}

.login-shell {
  position: relative;
  z-index: 1;
  min-height: 100vh;
  max-width: 1240px;
  margin: 0 auto;
  padding: 48px 32px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(380px, 460px);
  gap: 56px;
  align-items: center;
}

.login-showcase {
  max-width: 560px;
}

.login-showcase__eyebrow {
  margin: 0 0 18px;
  font-size: 13px;
  letter-spacing: 0.28em;
  color: rgba(203, 215, 255, 0.8);
}

.login-showcase__title {
  margin: 0;
  font-size: clamp(42px, 6vw, 64px);
  line-height: 1.05;
  font-weight: 700;
}

.login-showcase__description {
  margin: 18px 0 0;
  max-width: 560px;
  font-size: 17px;
  line-height: 1.8;
  color: rgba(231, 236, 246, 0.8);
}

.login-showcase__subtitle {
  margin: 14px 0 0;
  font-size: 18px;
  line-height: 1.4;
  letter-spacing: 0.08em;
  color: rgba(162, 226, 255, 0.92);
  text-transform: uppercase;
}

.login-showcase__highlights {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 24px;
}

.login-showcase__highlights span {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(10, 20, 36, 0.28);
  color: rgba(224, 232, 245, 0.82);
  font-size: 12px;
  letter-spacing: 0.08em;
}

.login-showcase__stats {
  margin-top: 38px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.stat-card {
  padding: 20px 18px;
  border-radius: 24px;
  background: rgba(10, 20, 36, 0.38);
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(14px);
}

.stat-card__value {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: #ffffff;
}

.stat-card__label {
  display: block;
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.6;
  color: rgba(219, 227, 244, 0.72);
}

.login-panel {
  padding: 32px;
  border-radius: 32px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.45);
  box-shadow: 0 28px 80px rgba(7, 17, 31, 0.28);
  backdrop-filter: blur(22px);
}

html.dark .login-panel {
  background: rgba(12, 20, 34, 0.9);
  border-color: rgba(255, 255, 255, 0.1);
  box-shadow: 0 28px 80px rgba(0, 0, 0, 0.4);
}

.login-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 26px;
}

.login-panel__kicker {
  margin: 0 0 10px;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.14em;
  color: #6f7ea3;
}

html.dark .login-panel__kicker {
  color: rgba(181, 196, 233, 0.72);
}

.login-panel__title {
  margin: 0;
  color: #132238;
  font-size: 30px;
  line-height: 1.2;
}

.login-panel__caption {
  margin: 10px 0 0;
  max-width: 320px;
  color: #6f7ea3;
  font-size: 13px;
  line-height: 1.6;
}

html.dark .login-panel__caption {
  color: rgba(181, 196, 233, 0.72);
}

html.dark .login-panel__title {
  color: #f4f7fb;
}

.login-panel__badge {
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(97, 76, 255, 0.1);
  color: #5f54ff;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

html.dark .login-panel__badge {
  background: rgba(122, 92, 255, 0.18);
  color: #d6cdff;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

.login-form :deep(.el-input__wrapper) {
  min-height: 52px;
  border-radius: 18px;
  background: rgba(245, 247, 251, 0.92);
  box-shadow: inset 0 0 0 1px rgba(133, 150, 179, 0.18);
}

html.dark .login-form :deep(.el-input__wrapper) {
  background: rgba(18, 28, 46, 0.92);
  box-shadow: inset 0 0 0 1px rgba(173, 188, 220, 0.14);
}

.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: inset 0 0 0 1px rgba(95, 84, 255, 0.65);
}

.login-form :deep(.el-input__inner) {
  color: #132238;
}

html.dark .login-form :deep(.el-input__inner) {
  color: #f4f7fb;
}

.input-icon {
  width: 16px;
  height: 16px;
  color: #8290ad;
}

.login-form__captcha-row {
  :deep(.el-form-item__content) {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 132px;
    gap: 12px;
  }
}

.login-captcha {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 52px;
  border: 0;
  border-radius: 18px;
  background: rgba(245, 247, 251, 0.92);
  box-shadow: inset 0 0 0 1px rgba(133, 150, 179, 0.18);
  cursor: pointer;
  padding: 0 10px;
}

html.dark .login-captcha {
  background: rgba(18, 28, 46, 0.92);
  box-shadow: inset 0 0 0 1px rgba(173, 188, 220, 0.14);
}

.login-captcha__img {
  display: block;
  max-width: 100%;
  height: 38px;
}

.login-form__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  color: #5b6782;
}

html.dark .login-form__meta {
  color: #c4d0e6;
}

.login-form__link {
  color: #5f54ff;
  font-size: 14px;
  text-decoration: none;
}

.login-form__link:hover {
  color: #4b42e6;
}

.login-form__action {
  margin-top: 8px;
  margin-bottom: 0;
}

.login-form__submit {
  width: 100%;
  min-height: 52px;
  border-radius: 18px;
  border: 0;
  background: linear-gradient(135deg, #5f54ff 0%, #4ea8ff 100%);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.1em;
}

.login-form__submit:hover,
.login-form__submit:focus {
  background: linear-gradient(135deg, #5548ff 0%, #399dff 100%);
}

.login-panel__footer {
  margin: 24px 0 0;
  text-align: center;
  font-size: 12px;
  color: #7f8aa3;
}

html.dark .login-panel__footer {
  color: rgba(196, 208, 230, 0.68);
}

@media (max-width: 1080px) {
  .login-shell {
    grid-template-columns: 1fr;
    gap: 32px;
    justify-items: center;
  }

  .login-showcase {
    max-width: 680px;
    text-align: center;
  }

  .login-showcase__description {
    margin-left: auto;
    margin-right: auto;
  }
}

@media (max-width: 768px) {
  .login-shell {
    padding: 24px 16px 32px;
  }

  .login-showcase {
    display: none;
  }

  .login-panel {
    width: 100%;
    max-width: 460px;
    padding: 24px;
    border-radius: 24px;
  }

  .login-panel__header {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 480px) {
  .login-panel {
    padding: 20px;
  }

  .login-form__meta {
    flex-direction: column;
    align-items: flex-start;
  }

  .login-form__captcha-row {
    :deep(.el-form-item__content) {
      grid-template-columns: 1fr;
    }
  }
}
</style>
