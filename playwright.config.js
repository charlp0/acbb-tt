const {defineConfig}=require('@playwright/test');
module.exports=defineConfig({
 testDir:'tests',testMatch:'browser.spec.js',workers:1,reporter:'line',
 use:{baseURL:'http://127.0.0.1:8766',headless:true,
   launchOptions:process.env.ACBB_CHROME?{executablePath:process.env.ACBB_CHROME}:{}},
 webServer:{command:'python3 -m http.server 8766 --bind 127.0.0.1 --directory build/public',url:'http://127.0.0.1:8766',reuseExistingServer:false},
});
