"""Browser tests for stemmate-backend-slice.html.
Setup once:  pip install playwright   then   playwright install chromium
Run:         python test_backend_slice.py   (use python3 on Mac/Linux)
Save the terminal output as your test evidence."""
import asyncio, sys
from playwright.async_api import async_playwright
from pathlib import Path
URL=(Path(__file__).parent/"stemmate-backend-slice.html").resolve().as_uri()
res=[]
def ck(name,cond):
    res.append((name,bool(cond))); print(("PASS " if cond else "FAIL ")+name)
async def login(pg,email,pw):
    await pg.fill('#email',email); await pg.fill('#password',pw); await pg.click('#loginForm button[type=submit]')
async def fill_valid(pg,title="Paper Plane"):
    await pg.fill('#title',title); await pg.fill('#steps',"Fold three planes\nThrow each one\nMeasure"); await pg.fill('#minutes',"45")
    await pg.fill('#materials',"Paper, tape measure"); await pg.fill('#safety',"Throw away from faces"); await pg.fill('#inclusion',"Pair learners so everyone has a role")
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); ctx=await b.new_context(); pg=await ctx.new_page()
        errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto(URL)
        await login(pg,'facilitator1@example.org','wrong')
        e1=await pg.inner_text('#loginErr')
        await login(pg,'nobody@example.org','wrong'); e2=await pg.inner_text('#loginErr')
        ck("T-login bad password and unknown email give the same message", e1==e2 and 'not correct' in e1)
        await login(pg,'','' ); ck("T-login empty fields explained", 'Enter your email' in await pg.inner_text('#loginErr'))
        await login(pg,'facilitator1@example.org','Demo-Pass-1'); await pg.wait_for_selector('#app:not([hidden])')
        ck("T-login good credentials open the workspace", 'Facilitator 1' in await pg.inner_text('#who'))
        await pg.click('#planForm button[type=submit]')
        n=0
        for k in ['title','steps','minutes','materials','safety','inclusion']:
            if (await pg.inner_text('#e-'+k)).strip(): n+=1
        ck("T-validate empty plan shows 6 field errors (got %d)"%n, n==6)
        ck("T-validate nothing stored for invalid plan", 'No saved plans' in await pg.inner_text('#plans'))
        await fill_valid(pg); await pg.fill('#minutes','999'); await pg.click('#planForm button[type=submit]')
        ck("T-validate minutes out of range refused", 'between 5 and 240' in await pg.inner_text('#e-minutes'))
        # autosave + restore
        await pg.fill('#minutes','45'); await pg.wait_for_timeout(700)
        ck("T-autosave draft note shown", 'Draft saved' in await pg.inner_text('#draftNote'))
        await pg.reload(); await pg.wait_for_selector('#app:not([hidden])')
        ck("T-autosave draft restored after reload", await pg.input_value('#title')=="Paper Plane" and await pg.input_value('#minutes')=="45")
        # offline save -> Pending
        await pg.check('#offlineToggle'); await pg.click('#planForm button[type=submit]'); await pg.wait_for_timeout(500)
        txt=await pg.inner_text('#plans'); ck("T-offline save shows Pending and keeps plan", 'Pending' in txt and 'Paper Plane' in txt)
        ck("T-offline save banner says Pending", 'Pending' in await pg.inner_text('#status'))
        ck("T-nothing reached server while offline", 'held by the simulated server: 0' in await pg.inner_text('#serverCount'))
        # back online -> Synced
        await pg.uncheck('#offlineToggle'); await pg.wait_for_timeout(600)
        ck("T-reconnect syncs plan to Synced", 'Synced' in await pg.inner_text('#plans') and 'server: 1' in await pg.inner_text('#serverCount'))
        # duplicate: sync again no double
        await pg.click('#syncNow'); await pg.wait_for_timeout(300)
        ck("T-repeat sync does not duplicate", 'server: 1' in await pg.inner_text('#serverCount'))
        # server rejects -> Failed, local kept, retry works
        await fill_valid(pg,"Leaf Detectives"); await pg.check('#rejectToggle'); await pg.click('#planForm button[type=submit]'); await pg.wait_for_timeout(500)
        txt=await pg.inner_text('#plans'); ck("T-rejected plan shows Failed with reason and local copy kept", 'Failed' in txt and 'still saved on this device' in txt and 'Leaf Detectives' in txt)
        ck("T-banner shows Failed with text", 'failed to send' in await pg.inner_text('#status'))
        await pg.uncheck('#rejectToggle'); await pg.click('#syncNow'); await pg.wait_for_timeout(500)
        ck("T-retry after fix reaches Synced", (await pg.inner_text('#plans')).count('Synced')==2 and 'server: 2' in await pg.inner_text('#serverCount'))
        # edit
        await pg.click('button[data-edit]'); await pg.wait_for_timeout(400)
        ck("T-edit loads plan into form", await pg.input_value('#title') in ("Paper Plane","Leaf Detectives"))
        await pg.fill('#title','Leaf Detectives v2'); await pg.click('#planForm button[type=submit]'); await pg.wait_for_timeout(600)
        t=await pg.inner_text('#plans'); ck("T-edit updates same plan (still 2 plans) and re-syncs", t.count('Synced')==2 and 'v2' in t and 'server: 2' in await pg.inner_text('#serverCount'))
        # workspace separation
        await pg.click('#logout'); await login(pg,'facilitator2@example.org','Demo-Pass-2'); await pg.wait_for_selector('#app:not([hidden])'); await pg.wait_for_timeout(500)
        ck("T-workspace second facilitator sees none of the first's plans", 'No saved plans' in await pg.inner_text('#plans') and await pg.input_value('#title')=="")
        await pg.click('#logout'); await login(pg,'facilitator1@example.org','Demo-Pass-1'); await pg.wait_for_selector('#app:not([hidden])'); await pg.wait_for_timeout(500)
        ck("T-workspace first facilitator's plans still there", 'Leaf Detectives' in await pg.inner_text('#plans'))
        ck("T-no JavaScript errors on the page", not errs)
        await b.close()
    bad=[n for n,o in res if not o]; print("\n%d/%d passed"%(len(res)-len(bad),len(res))); print("FAILED:",bad)
asyncio.run(main())
