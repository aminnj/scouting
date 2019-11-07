import numba
import numpy as np
import functools

def set_plotting_style():
    from matplotlib import rcParams
    rcParams["font.family"] = "sans-serif"
    rcParams["font.sans-serif"] = ["Helvetica", "Arial", "Liberation Sans", "Bitstream Vera Sans", "DejaVu Sans"]
    rcParams['legend.fontsize'] = 11
    rcParams['legend.labelspacing'] = 0.2
    rcParams['hatch.linewidth'] = 0.5  # https://stackoverflow.com/questions/29549530/how-to-change-the-linewidth-of-hatch-in-matplotlib
    rcParams['axes.xmargin'] = 0.0 # rootlike, no extra padding within x axis
    rcParams['axes.labelsize'] = 'x-large'
    rcParams['axes.formatter.use_mathtext'] = True
    rcParams['legend.framealpha'] = 0.65
    rcParams['axes.labelsize'] = 'x-large'
    rcParams['axes.titlesize'] = 'large'
    rcParams['xtick.labelsize'] = 'large'
    rcParams['ytick.labelsize'] = 'large'
    rcParams['figure.subplot.hspace'] = 0.1
    rcParams['figure.subplot.wspace'] = 0.1
    rcParams['figure.subplot.right'] = 0.96
    rcParams['figure.max_open_warning'] = 0
    rcParams['figure.dpi'] = 100
    rcParams["axes.formatter.limits"] = [-5,4] # scientific notation if log(y) outside this
    
@numba.njit()
def compute_bin_1d_uniform(x, bins, overflow=False):
    n = bins.shape[0] - 1
    b_min = bins[0]
    b_max = bins[-1]
    if overflow:
        if x > b_max: return n-1
        elif x < b_min: return 0
    ibin = int(n * (x - b_min) / (b_max - b_min))
    if x < b_min or x > b_max:
        return -1
    else:
        return ibin
    
@numba.njit()
def numba_histogram(a, bins, weights=None,overflow=False):
    db = np.ediff1d(bins)
    is_uniform_binning = np.all(db-db[0]<1e-6)
    hist = np.zeros((len(bins)-1,), dtype=np.float64)
    a = a.flat
    b_min = bins[0]
    b_max = bins[-1]
    n = bins.shape[0] - 1
    if weights is None:
        weights = np.ones(len(a),dtype=np.float64)
    if is_uniform_binning:
        for i in range(len(a)):
            ibin = compute_bin_1d_uniform(a[i], bins, overflow=overflow)
            if ibin >= 0:
                hist[ibin] += weights[i]
    else:
        ibins = np.searchsorted(bins, a, side='left')
        for i in range(len(a)):
            ibin = ibins[i]
            if overflow:
                if ibin == n+1: ibin = n
                elif ibin == 0: ibin = 1
            if ibin >= 1 and ibin <= n:
                hist[ibin-1] += weights[i]
        pass
    return hist, bins

@numba.njit()
def numba_histogram2d(ax,ay, bins_x, bins_y, weights=None,overflow=False):
    db_x = np.ediff1d(bins_x)
    db_y = np.ediff1d(bins_y)
    is_uniform_binning_x = np.all(db_x-db_x[0]<1e-6)
    is_uniform_binning_y = np.all(db_y-db_y[0]<1e-6)
    hist = np.zeros((len(bins_x)-1,len(bins_y)-1), dtype=np.float64)
    ax = ax.flat
    ay = ay.flat
    b_min_x = bins_x[0]
    b_max_x = bins_x[-1]
    n_x = bins_x.shape[0] - 1
    b_min_y = bins_y[0]
    b_max_y = bins_y[-1]
    n_y = bins_y.shape[0] - 1
    if weights is None:
        weights = np.ones(len(ax),dtype=np.float64)
    if is_uniform_binning_x and is_uniform_binning_y:
        for i in range(len(ax)):
            ibin_x = compute_bin_1d_uniform(ax[i], bins_x, overflow=overflow)
            ibin_y = compute_bin_1d_uniform(ay[i], bins_y, overflow=overflow)
            if ibin_x >= 0 and ibin_y >= 0:
                hist[ibin_x,ibin_y] += weights[i]
    else:
        ibins_x = np.searchsorted(bins_x, ax, side='left')
        ibins_y = np.searchsorted(bins_y, ay, side='left')
        for i in range(len(ax)):
            ibin_x = ibins_x[i]
            ibin_y = ibins_y[i]
            if overflow:
                if ibin_x == n_x+1: ibin_x = n_x
                elif ibin_x == 0: ibin_x = 1
                if ibin_y == n_y+1: ibin_y = n_y
                elif ibin_y == 0: ibin_y = 1
            if ibin_x >= 1 and ibin_y >= 1 and ibin_x <= n_x and ibin_y <= n_y:
                hist[ibin_x-1,ibin_y-1] += weights[i]
    return hist, bins_x, bins_y

def make_profile(tobin,toreduce,edges=None,errors=True):
    from scipy.stats import binned_statistic
    yvals = binned_statistic(tobin,toreduce, 'mean', bins=edges).statistic
    yerr = None
    if errors:
        yerr = binned_statistic(tobin,toreduce, 'std', bins=edges).statistic/binned_statistic(tobin,toreduce, 'count', bins=edges).statistic**0.5
    return yvals, yerr


@functools.lru_cache(maxsize=256)
def get_chunking(filelist, chunksize, treename="Events", workers=12, skip_bad_files=False):
    """
    Return 2-tuple of
    - chunks: triplets of (filename,entrystart,entrystop) calculated with input `chunksize` and `filelist`
    - total_nevents: total event count over `filelist`
    """
    import uproot
    import awkward
    from tqdm.auto import tqdm
    import concurrent.futures
    chunksize = int(chunksize)
    chunks = []
    nevents = 0
    if skip_bad_files:
        # slightly slower (serial loop), but can skip bad files
        for fname in tqdm(filelist):
            try:
                items = uproot.numentries(fname, treename, total=False).items()
            except (IndexError, ValueError) as e:
                print("Skipping bad file", fname)
                continue
            for fn, nentries in items:
                nevents += nentries
                for index in range(nentries // chunksize + 1):
                    chunks.append((fn, chunksize*index, min(chunksize*(index+1), nentries)))
    elif filelist[0].endswith(".awkd"):
        for fname in tqdm(filelist):
            f = awkward.load(fname,whitelist=awkward.persist.whitelist + [['blosc', 'decompress']])
            nentries = len(f["run"])
            nevents += nentries
            for index in range(nentries // chunksize + 1):
                chunks.append((fname, chunksize*index, min(chunksize*(index+1), nentries)))
    else:
        executor = None if len(filelist) < 5 else concurrent.futures.ThreadPoolExecutor(min(workers, len(filelist)))
        for fn, nentries in uproot.numentries(filelist, treename, total=False, executor=executor).items():
            nevents += nentries
            for index in range(nentries // chunksize + 1):
                chunks.append((fn, chunksize*index, min(chunksize*(index+1), nentries)))
    return chunks, nevents

@functools.lru_cache(maxsize=256)
def get_chunking_dask(filelist, chunksize, client=None, treename="Events"):
    import uproot
    chunks, chunksize, nevents = [], int(chunksize), 0
    info = client.gather(client.map(lambda x:(x,uproot.numentries(x,treename)), filelist))
    for fn, nentries in info:
        nevents += nentries
        for index in range(nentries // chunksize + 1):
            chunks.append((fn, chunksize*index, min(chunksize*(index+1), nentries)))
    return chunks, nevents


def get_geometry_df(fname):
    """
    Get pixel geometry from inputs made in `geometry/`
    """
    import uproot
    import numpy as np
    f = uproot.open(fname)
    t = f["idToGeo"]
    df = t.pandas.df(branches=["shape","translation","matrix"],flatten=False)
    df["translation_x"] = df["translation"].str[0]
    df["translation_y"] = df["translation"].str[1]
    df["translation_z"] = df["translation"].str[2]
    df["translation_rho"] = np.hypot(df["translation_x"],df["translation_y"])
    df = df[df["shape"].apply(lambda x:x[0])==2.]
    df = df.query("translation_rho<18") # 4 pixel layers
    return df


def plot_overlay_bpix(ax,**kwargs):
    """
    Given an axes object, overlays 2D lines for the transverse projection of the first 3 bpix layers
    Note the hardcoded geometry path
    """
    import numpy as np
    color = kwargs.pop("color","k")
    binary_triplets = np.unpackbits(np.arange(8,dtype=np.uint8)[:,np.newaxis],1)[:,-3:].astype(int)
    step_directions = binary_triplets*2-1
    gdf = get_geometry_df("/home/users/namin/2019/scouting/repo/geometry/tracker_geometry_data2018.root")
    expand_l = kwargs.pop("expand_l",0.1)
    expand_w = kwargs.pop("expand_w",0.1)
    expand_h = kwargs.pop("expand_h",0.2)
    do_expand = (expand_h > 0) or (expand_w > 0) or (expand_h)
    for irow,entry in gdf.query("0 < translation_z < 8 and translation_rho<14").iterrows():
        shape = entry["shape"][1:-1].T
        if do_expand:
            newshape = np.array(shape)
            newshape[0] += expand_l
            newshape[1] += expand_w
            newshape[2] += expand_h
            shape = newshape
        translation = entry["translation"]
        matrix = entry["matrix"].reshape(3,3)
        points = shape * step_directions
        points = np.array([np.dot(matrix,point)+translation for point in points])
        points = points[np.array([6,2,1,5,6])]
        ax.plot(points[:,0],points[:,1],color=color,**kwargs)
    return ax
