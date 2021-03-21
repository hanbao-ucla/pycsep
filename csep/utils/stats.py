import numpy
import scipy.stats
import scipy.special

def sup_dist(cdf1, cdf2):
    """
    given two cumulative distribution functions, compute the supremum of the set of absolute distances.

    note:
        this function does not check that the ecdfs are ordered or balanced. beware!
    """
    return numpy.max(numpy.absolute(cdf2 - cdf1))

def sup_dist_na(data1, data2):
    """
    computes the ks statistic for two ecdfs that are not necessarily aligned on the same values. performs this
    operation by merging the two datasets together. this is taken from the 2sample ks test in the scipy codebase

    Args:
        data1: (numpy array like)
        data2: (numpy array like)

    Returns:
        ks: sup dist from the two cdf functions
    """
    data1, data2 = map(numpy.asarray, (data1, data2))
    n1 = len(data1)
    n2 = len(data2)
    data1 = numpy.sort(data1)
    data2 = numpy.sort(data2)
    data_all = numpy.concatenate([data1,data2])
    cdf1 = numpy.searchsorted(data1,data_all,side='right')/(1.0*n1)
    cdf2 = (numpy.searchsorted(data2,data_all,side='right'))/(1.0*n2)
    d = numpy.max(numpy.absolute(cdf1-cdf2))
    return d

def cumulative_square_diff(cdf1, cdf2):
    """
    given two cumulative distribution functions, compute the cumulative sq. diff of the set of distances.

    note:
        this function does not check that the ecdfs are ordered or balanced. beware!

    Args:
        cdf1: ndarray
        cdf2: ndarray

    Returns:
        cum_dist: scalar distance metric for the histograms

    """
    return numpy.sum((cdf2 - cdf1)**2)

def binned_ecdf(x, vals):
    """
    returns the statement P(X ≤ x) for val in vals.
    vals must be monotonically increasing and unqiue.

    returns:
        tuple: sorted vals, and ecdf computed at vals
    """
    # precompute ecdf for x: returns(sorted(x), ecdf())
    if len(x) == 0:
        return None
    ex, ey = ecdf(x)
    cdf = numpy.array(list(map(lambda val: less_equal_ecdf(x, val, cdf=(ex, ey)), vals)))
    return vals, cdf

def ecdf(x):
    """
    Compute the ecdf of vector x. This does not contain zero, should be equal to 1 in the last value
    to satisfy F(x) == P(X ≤ x).

    Args:
        x (numpy.array): vector of values

    Returns:
        xs (numpy.array), ys (numpy.array)
    """
    xs = numpy.sort(x)
    ys = numpy.arange(1, len(x) + 1) / float(len(x))
    return xs, ys

def greater_equal_ecdf(x, val, cdf=()):
    """
    Given val return P(x ≥ val).

    Args:
        x (numpy.array): set of values
        val (float): value
        ecdf (tuple): ecdf of x, should be tuple (sorted(x), ecdf(x))

    Returns:
        (float): probability that x ≤ val
    """
    x = numpy.asarray(x)
    if x.shape[0] == 0:
        return None
    if not cdf:
        ex, ey = ecdf(x)
    else:
        ex, ey = cdf

    eyc = ey[::-1]

    # some short-circuit cases for discrete distributions; x is sorted, but reversed.
    if val > ex[-1]:
        return 0.0
    if val < ex[0]:
        return 1.0
    return eyc[numpy.searchsorted(ex, val)]

def less_equal_ecdf(x, val, cdf=()):
    """
    Given val return P(x ≤ val).

    Args:
        x (numpy.array): set of values
        val (float): value

    Returns:
        (float): probability that x ≤ val
    """
    x = numpy.asarray(x)
    if x.shape[0] == 0:
        return None
    if not cdf:
        ex, ey = ecdf(x)
    else:
        ex, ey = cdf
    # some short-circuit cases for discrete distributions
    if val > ex[-1]:
        return 1.0
    if val < ex[0]:
        return 0.0
    # uses numpy implementation of binary search
    return ey[numpy.searchsorted(ex, val, side='right') - 1]

def min_or_none(x):
    """
    Given an array x, returns the min value. If x = [], returns None.
    """
    if len(x) == 0:
        return None
    else:
        return numpy.min(x)

def max_or_none(x):
    """
    Given an array x, returns the max value. If x = [], returns None.
    """
    if len(x) == 0:
        return None
    else:
        return numpy.max(x)

def get_quantiles(sim_counts, obs_count):
    """ Computes delta1 and delta2 quantile scores from empirical distribution and observation """
    # delta 1 prob of observation at least n_obs events given the forecast
    delta_1 = greater_equal_ecdf(sim_counts, obs_count)
    # delta 2 prob of observing at most n_obs events given the catalog
    delta_2 = less_equal_ecdf(sim_counts, obs_count)
    return delta_1, delta_2

def poisson_log_likelihood(observation, forecast):
    """ Wrapper around scipy to compute the Poisson log-likelihood

    Args:
        observation: Observed (Grided) seismicity
        forecast: Forecast of a Model (Grided)

    Returns:
        Log-Liklihood values of between binned-observations and binned-forecasts
    """
    return numpy.log(scipy.stats.poisson.pmf(observation, forecast))

def poisson_joint_log_likelihood_ndarray(target_event_log_rates, target_observations, n_fore):
    """ Efficient calculation of joint log-likelihood of grid-based forecast.

    Note: log(w!) = 0

    Args:
        target_event_log_rates: natural log of bin rates where target events occurred
        target_observations: counts of target events
        n_fore: expected number from the forecasts

    Returns:
        joint_log_likelihood

    """
    sum_log_target_event_rates = numpy.sum(target_event_log_rates)
    # factorial(n) = loggamma(n+1)
    discrete_penalty_term = numpy.sum(scipy.special.loggamma(target_observations+1))
    return sum_log_target_event_rates - discrete_penalty_term - n_fore

def poisson_inverse_cdf(random_matrix, lam):
    """ Wrapper around scipy inverse poisson cdf function

    Args:
        random_matrix: Matrix of dimenions equal to forecast, containing random
                       numbers between 0 and 1.
        lam: vector of parameters for poisson distribution

    Returns:
        sample from the poisson distribution
    """
    return scipy.stats.poisson.ppf(random_matrix, lam)

def get_Kagan_I1_score(forecast, catalogs):
    """
    A program for scoring (I_1) earthquake-forecast grids by the methods of:
    Kagan, Yan Y. [2009] Testing long-term earthquake forecasts: likelihood methods
                         and error diagrams, Geophys. J. Int., v. 177, pages 532-542.
    Some advantages of these methods are that they:
        -are insensitive to the grid used to cover the Earth;
        -are insensitive to changes in the overall seismicity rate;
        -do not modify the locations or magnitudes of test earthquakes;
        -do not require simulation of virtual catalogs;
        -return relative quality measures, not just "pass" or "fail;" and
        -indicate relative specificity of forecasts as well as relative success.
    
    Written by Han Bao, UCLA, March 2021.
    
    Args:
        forecast:  csep.forecast 
        catalogs:  csep.catalog or a list of csep.catalog (catalogs to test against the forecast)
        
    Note that: 
        (1) the testing catalog and forecast should have exactly the same time-window (duration)
        (2) grids of forecast has to be regular rectangular shape that are defined by 
            [min_lat,max_lat,d_lat; min_lon,max_lon,d_lon]. And the grids are ordered as such:
            it scan through the rectangular region from [min_lat,min_lon] to [max_lat,min_lon], 
            than move to next longitude line, i.e. from [min_lat+d_lat,min_lon] to [max_lat+d_lat,min_lon].
            The gridded region can be the entire globe. (THIS IS IMPORTANT TO FIND WHICH BIN DOES EACH
            TESTED EVENT FALLS IN)

    Returns:
       I_1
    """
    ### Determine if input 'catalogs' is a list of csep.catalogs or a single csep.catalog
    try:
        N_cat = len(catalogs) # the input catalogs is a list of csep.catalogs
    except:  
        N_cat = 1             # the input catalogs is a single csep.catalog
        catalogs = [catalogs]
            
    earth_radius_km = 6371.
    R2 = earth_radius_km ** 2
    rad_per_deg = np.pi / 180.0e0
    
    ### GET area for each geological bin (cell)
    bin_lat = forecast.get_latitudes()                   # bin location in forecast
    bin_lon = forecast.get_longitudes()                  # bin location in forecast
    rate    = forecast.spatial_counts()                  # [eq per cell per duration] in forecast
    lats = np.unique(bin_lat) 
    lons = np.unique(bin_lon)
    min_lat = np.min(lats); max_lat = np.max(lats) # get min/max of grids' lat
    min_lon = np.min(lons); max_lon = np.max(lons) # get min/max of grids' lon
    d_lat = lats[1] - lats[0]                      # get grid interval [d_lat]
    d_lon = lons[1] - lons[0]                      # get grid interval [d_lon]
    area_km2 = np.zeros(bin_lon.shape, dtype=np.float64) # Initialze
    for i, bot_lat in enumerate(bin_lat):
        bot_lon = bin_lon[i]
        top_lat = bot_lat + d_lat
        top_lon = bot_lon + d_lon
        strip_area_steradian = 2 * np.pi * (1.0e0 - np.cos((90.0e0 - bot_lat) * rad_per_deg)) \
                             - 2 * np.pi * (1.0e0 - np.cos((90.0e0 - top_lat) * rad_per_deg))
        area_km2[i] = strip_area_steradian * R2 / (360.0/d_lon)
    total_area = np.sum(area_km2) # Total Area
    
    # Get Rate Density and uniform_forecast of the Forecast
    rateDen = rate/area_km2                      # Rate Density for all bins
    uniform_forecast = np.sum(rate)/total_area   # Uniform Forecast
    
    ### GET Contribution Scores (of I_1) from each event in the testing Catalog
    I_1   = np.zeros((N_cat,), dtype=np.float64)
    for j,subcatalog in enumerate(catalogs):
        evt_lat = subcatalog.get_latitudes()     # event location in the testing catalog
        evt_lon = subcatalog.get_longitudes()    # event location in the testing catalog
        N_event = subcatalog.event_count         # total number of events of the testing catalog

        score    = np.zeros(evt_lon.shape, dtype=np.float64) # initialize
        for i in np.arange(N_event):
            idx = int( np.floor((evt_lon[i] - (min_lon)) * (1.0/d_lon)) ) * len(lats) \
                + int( np.floor((evt_lat[i] - (min_lat)) * (1.0/d_lat)) ) 
            score[i] = np.log2(rateDen[idx]/uniform_forecast)
        ### GET I_1 score
        I_1[j] = sum(score)/N_event
    
    return I_1