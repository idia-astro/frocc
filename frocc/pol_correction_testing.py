#!/users/lennart/venv/bin/python3
import numpy as np 
import pandas as pd
from io import StringIO

# below is 
# Do you see this? <--------------
#  ok, cool
# so, below is basically you code
def rotate_spectra(freqs, rotate_file_path='/idia/projects/mightee/mightee-pol/processed/cube_rotation_angles.txt'):
    """
    Given the input FITS name, rotates the cubes on the fly before making the plots.
    If the FITS name does not exist in the input text file, it skips plotting it entirely if do_rotate=True in the top cell.
    """

    skip_rotate = False

    #df = pd.read_csv(rotate_file_path, header=3, delim_whitespace=True)
    df = pd.read_csv("/idia/projects/mightee/mightee-pol/processed/cube_rotation_angles.txt", header=3, delim_whitespace=True)
    print(df.describe())

#    basename = os.path.basename(fitsname)
#    obsid = int(basename.split('_')[0])
    obsid = "1538856059"

#    idx = np.where(df['obsid'] == obsid)
#    df = df.iloc[idx]


#    if df.size == 0:
#        skip_rotate = True
#        return skip_rotate, 0, 0

    # in your code it looks like as if you are taking... whait a mom..
    coeffsXY = [df['coeffsXY_a'].to_numpy()[0], df['coeffsXY_b'].to_numpy()[0], df['coeffsXY_c'].to_numpy()[0]]
    coeffsPol = [df['coeffsPol_a'].to_numpy()[0], df['coeffsPol_b'].to_numpy()[0], df['coeffsPol_c'].to_numpy()[0]]

    polyXY = np.poly1d(coeffsXY)
    polyPol = np.poly1d(coeffsPol)

    # oh here, you are taking only the first freq. That doesn't look right.
    # freqs is a list, so np.asarray(freqs) is an array of length 1 somehow. So to get the "actual" array I have to take [0] if that makes sense. To check, just print freqs before this line
    freqs = np.asarray(freqs)[0]

    xyph = polyXY(freqs)
    polph = polyPol(freqs)
    # look, I'm printing xyph and polph. Wouldn't I expect an array or corrections then?
    print("!!!!!!!!!!!!")
    # that's it. just one value
    print(xyph)
    input()
    print(polph)
    input()

# here is mine
def second_order_poly(x, a, b, c):
    #y = a*x**2 + b*x + c
    # here was the issue!
    # it used to be:
    poly = np.poly1d(a, b, c)
    # and it wouldn't complain but return the... oh what, it would 
    # nicely done! not an easy bug to spot and fix. Do they match now?
    poly = np.poly1d([a[0], b[0], c[0]])
    y = poly(x) # <-- return freq here (for y)
    print(y)
    input("!!!!!!!!!!!!!!!!!")
    return y

def get_correction_coefficients(obsid):
    try:
#        info(f"Reading coefficient file with rotation parameters: {conf.input.fileXYphasePolAngleCoeffs}")
#        with open("/idia/projects/mightee/mightee-pol/processed/cube_rotation_angles.txt", "r") as f:
#            rawString = f.read()
#        headerBody = (rawString[rawString.rfind("#")+1:]).strip().replace("  ", " ")
#        data = pd.read_csv(StringIO(headerBody), sep=" ")
# just reading the cooefs file into a df
        data = pd.read_csv("/idia/projects/mightee/mightee-pol/processed/cube_rotation_angles.txt", header=3, delim_whitespace=True)
        print(data)
    except Exception as e:
        print(e)

    #data = pd.DataFrame([x.split(' ') for x in result.split('\n')])
    data = data[data['obsid'].astype(str) == str(obsid)]
    return data

def check_rotation(freqs):
    for freq in freqs:
        print("Starting XY phase and pol angle rotation.")
        # grep obsid from MS filename. TODO: find something better
        #basename = os.path.basename(os.path.normpath(conf.input.inputMS[0]))
        #obsid = re.search(r"[0-9]{10}", basename)[0]
        # hard coded obsid for testing
        obsid = "1538856059"
        print(f"Uning observation ID (obsid): {obsid}")

# let's have a look what happens here:
        coeffs = get_correction_coefficients(obsid)
        print(f"Using correction coefficients: {coeffs.to_dict()}")
        print(f'Image frequency : {freq}')

        # correctXYPhase
        coeffsXY_a = coeffs['coeffsXY_a'].to_numpy()
        coeffsXY_b = coeffs['coeffsXY_b'].to_numpy()
        coeffsXY_c = coeffs['coeffsXY_c'].to_numpy()
        # lets see what second_order_poly does
        xyPhaseAngle = second_order_poly(freq, coeffsXY_a, coeffsXY_b, coeffsXY_c)
        #xyPhaseAngle = xyPhaseAngle * np.pi/180
        print(f"Using xy-phase angle: {xyPhaseAngle}")
    #    stokesUtmp = stokesU*np.cos(xyPhaseAngle) - stokesV*np.sin(xyPhaseAngle)
    #    stokesVtmp = stokesU*np.sin(xyPhaseAngle) + stokesV*np.cos(xyPhaseAngle)

        # correctPolAngle
        coeffsPol_a = coeffs['coeffsPol_a'].to_numpy()
        coeffsPol_b = coeffs['coeffsPol_b'].to_numpy()
        coeffsPol_c = coeffs['coeffsPol_c'].to_numpy()
        polAngle = second_order_poly(freq, coeffsPol_a, coeffsPol_b, coeffsPol_c)
        #polAngle = polAngle * np.pi/180
        print(f"Using polarization angle: {polAngle}")
    #    stokesQtmp = stokesQ*np.cos(polAngle) - stokesUtmp*np.sin(polAngle)
    #    stokesUtmp = stokesQ*np.sin(polAngle) + stokesUtmp*np.cos(polAngle)
    #    stokesQ = stokesQtmp
    #    stokesU = stokesUtmp
    #    stokesV = stokesVtmp
    #    rmsDict["xyPhaseCorr"].append(xyPhaseAngle)
    #    rmsDict["polAngleCorr"].append(polAngle)
        input()

def main():
    # so i generate test freqs and feed it into the fct
    freqs = np.arange(880,1600, 2.5)
#    print(freqs)
#    check_rotation(freqs)
    rotate_spectra(freqs)
    # so, yeah, looks like this is done. testing it now
    # one question ... ..
    # alright super. Looks like it'll work now. 

if __name__ == "__main__":
    main()

