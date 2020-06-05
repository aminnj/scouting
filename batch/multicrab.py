import os
import sys
import multiprocessing
from CRABAPI.RawCommand import crabCommand
from CRABClient.UserUtilities import setConsoleLogLevel, config

import glob
from pprint import pprint
from metis.CrabManager import CrabManager

def get_proxy_file():
    return "/tmp/x509up_u{0}".format(os.getuid())

def get_config_for_era(era, version, do_unblind=False):
    # sorry, name might be stupid. `do_unblind` means we process
    # the unblinded subset only.

    # https://twiki.cern.ch/twiki/bin/view/CMSPublic/CRAB3ConfigurationFile
    cfg = config()

    cfg.General.requestName = 'skim_{}_{}{}'.format(
            era,
            version,
            ("_unblind" if do_unblind else "")
            )
    cfg.Data.inputDataset = '/ScoutingCaloMuon/Run{}-v1/RAW'.format(era)

    cfg.General.workArea = 'crab'
    cfg.General.transferLogs = True

    cfg.JobType.pluginName = 'Analysis'
    cfg.JobType.psetName = 'Scouting/NtupleMaker/test/producer.py'

    cfg.JobType.pyCfgParams=["era={}".format(era),"data=True",]

    cfg.Data.splitting = 'EventAwareLumiBased'
    cfg.Data.unitsPerJob = int(10e6)

    if "2018" in era:
        cfg.Data.lumiMask = "data/Cert_314472-325175_13TeV_PromptReco_Collisions18_JSON.txt"
    if "2017" in era:
        cfg.Data.lumiMask = "data/Cert_294927-306462_13TeV_EOY2017ReReco_Collisions17_JSON.txt"
    if do_unblind:
        cfg.Data.lumiMask = "data/Cert_2017-2018_10percentbyrun_JSON.txt"

    cfg.Data.publication = False
    cfg.Site.storageSite = "T2_US_UCSD"
    return cfg

def do_submit(q, config, proxy):
    extra = dict(config=config)
    if proxy: extra["proxy"] = proxy
    out = crabCommand('submit', **extra)
    q.put(out)

if __name__ == "__main__":

    version = "v12"
    do_unblind = False
    proxy = get_proxy_file()
    for era in [
            "2017C",
            "2017D",
            "2017E",
            "2017F",
            "2018A",
            "2018B",
            "2018C",
            "2018D",
            ]:
        cfg = get_config_for_era(era=era, version=version, do_unblind=do_unblind)
        taskdir = "{}/crab_{}/".format(cfg.General.workArea, cfg.General.requestName)
        if os.path.exists(taskdir):
            print("Task dir {} already exists.".format(taskdir))
            continue
        # need to spawn a new process or else crab complains that a config has already been cached :(
        mpq = multiprocessing.Queue()
        mpp = multiprocessing.Process(target=do_submit, args=(mpq, cfg, proxy))
        mpp.start()
        mpp.join()
        out = mpq.get()
        print(out)

    statuses = {}
    taskdirs = glob.glob("crab/crab_skim_201*_{}/".format(version))
    for taskdir in taskdirs:
        print("\n\n----- {} -----".format(taskdir))
        cm = CrabManager(request_name=taskdir)

        js = cm.crab_status()
        js.pop("job_info")
        pprint(js)

        statuses[taskdir] = js

        # try:
        #     js = cm.crab_resubmit()
        #     pprint(js)
        # except:
        #     pass

    src = """
<html>
<head>
<style>
.progress {
width: 40%;
}
</style>
<script src="https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/js/bootstrap.min.js" crossorigin="anonymous"></script>
<link href="https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/css/bootstrap.min.css" rel="stylesheet" crossorigin="anonymous">
</head>
<body>
    """
    for taskdir,info in statuses.items():
        job_breakdown = info["job_breakdown"]
        totjobs = sum(job_breakdown.values())
        if totjobs == 0: continue
        ndone = (job_breakdown["finished"])
        nrunning = (job_breakdown["running"]+job_breakdown["transferring"]+job_breakdown["transferred"])
        nfailed = (job_breakdown["failed"])
        nidle = (job_breakdown["unsubmitted"]+job_breakdown["idle"]+job_breakdown["cooloff"])
        div = """
{taskdir}
<div class="progress">
  <div class="progress-bar bg-success" role="progressbar" style="width:{pctdone}%">
  {ndone} done
  </div>
  <div class="progress-bar bg-info" role="progressbar" style="width:{pctrunning}%">
  {nrunning} running
  </div>
  <div class="progress-bar bg-danger" role="progressbar" style="width:{pctfailed}%">
  {nfailed} failed
  </div>
  <div class="progress-bar bg-warning" role="progressbar" style="width:{pctidle}%">
  {nidle} idle
  </div>
</div>
        """.format(
                ndone=ndone,
                nrunning=nrunning,
                nfailed=nfailed,
                nidle=nidle,
                pctdone=1.0*ndone/totjobs*100.,
                pctrunning=1.0*nrunning/totjobs*100.,
                pctfailed=1.0*nfailed/totjobs*100.,
                pctidle=1.0*nidle/totjobs*100.,
                taskdir=taskdir,
                )
        src += div

    src += "</body></html>"

    user = os.getenv("USER").strip()
    outdir = "/home/users/{}/public_html/dump/".format(user)
    if not os.path.exists(outdir):
        os.system("mkdir -p {}".format(outdir))
    with open("{}/test.html".format(outdir),"w") as fh:
        fh.write(src)


