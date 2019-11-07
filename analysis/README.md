## Environment and dependencies

Install conda and get all the dependencies:
```
curl -O -L https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b 

# adds conda to the end of ~/.bashrc, so relogin after executing this line
~/miniconda3/bin/conda init

# stops conda from activating the base environment on login
conda config --set auto_activate_base false
conda config --add channels conda-forge

conda create --name analysisenv uproot matplotlib pandas jupyter numba -y
```

Start analysis jupyter notebook:
```bash
conda activate analysisenv 
jupyter notebook --no-browser

# then execute on your local computer to forward the port, and visit the url
ssh -N -f -L localhost:1234:localhost:1234 uaf-10.t2.ucsd.edu
```


### Ntuple catalog

| Type          | Era           | >=2Mu,>=1DV skim? | >1cm DV skim? | Unblinded 1fb? | Path                                                                                  | Notes         |
| ------------- | ------------- | -------------     | ------------- | -------------  | -------------                                                                         | ------------- |
| Data          | 2018A         | x                 | x             |                | /hadoop/cms/store/user/namin/ProjectMetis/ScoutingCaloMuon_Run2018C-v1_RAW_v4skim1cm/ |               |
| Data          | 2018B         | x                 | x             |                | /hadoop/cms/store/user/namin/ProjectMetis/ScoutingCaloMuon_Run2018C-v1_RAW_v4skim1cm/ |               |
| Data          | 2018C         | x                 | x             |                | /hadoop/cms/store/user/namin/ProjectMetis/ScoutingCaloMuon_Run2018C-v1_RAW_v4skim1cm/ |               |
| Data          | 2018D         | x                 | x             |                | /hadoop/cms/store/user/namin/ProjectMetis/ScoutingCaloMuon_Run2018C-v1_RAW_v4skim1cm/ |               |
| Data          | 2018A         | x                 |               |                | /hadoop/cms/store/user/namin/ProjectMetis/ScoutingCaloMuon_Run2018C-v1_RAW_v4/        |               |
| Data          | 2018B         | x                 |               |                | /hadoop/cms/store/user/namin/ProjectMetis/ScoutingCaloMuon_Run2018C-v1_RAW_v4/        |               |
| Data          | 2018C         | x                 |               |                | /hadoop/cms/store/user/namin/ProjectMetis/ScoutingCaloMuon_Run2018C-v1_RAW_v4/        |               |
| Data          | 2018D         | x                 |               |                | /hadoop/cms/store/user/namin/ProjectMetis/ScoutingCaloMuon_Run2018C-v1_RAW_v4/        |               |
| MC            | 2018          |                   |               |                | /hadoop/cms/store/user/namin/DisplacedMuons/babies/baby_HToZZTo2Mu2X_ctau50mm.root    | ctau=50mm     |
