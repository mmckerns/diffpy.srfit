#!/usr/bin/env python
########################################################################
#
# diffpy.srfit      by DANSE Diffraction group
#                   Simon J. L. Billinge
#                   (c) 2009 Trustees of the Columbia University
#                   in the City of New York.  All rights reserved.
#
# File coded by:    Chris Farrow
#
# See AUTHORS.txt for a list of people who contributed.
# See LICENSE.txt for license information.
#
########################################################################
"""Example of combining PDF and SAS nanoparticles data. 

This is an example of using both PDF and SAS data in the same fit. Unlike
nppdfsas.py, this example does not use the SAS data directly to calculate f(r),
but refines a model to the SAS data and uses the model calculation for f(r).
This introduces a feedback mechanism into the fit that allows the PDF
refinement to guide the SAS refinement, and in the end gives the shape of the
nanoparticle that agrees best with both the PDF and SAS data.

"""

import numpy

from pyobjcryst.crystal import CreateCrystalFromCIF

from diffpy.srfit.pdf import PDFGenerator, PDFParser
from diffpy.srfit.sas import PrCalculator, SASParser, SASGenerator
from diffpy.srfit.fitbase import Profile
from diffpy.srfit.fitbase import FitContribution, FitRecipe
from diffpy.srfit.fitbase import FitResults

from gaussianrecipe import scipyOptimize
from nppdfsas import plotResults

def makeRecipe(ciffile, grdata, iqdata):
    """Make complex-modeling recipe where I(q) and G(r) are fit
    simultaneously.

    The fit I(q) is fed into the calculation of G(r), which provides feedback
    for the fit parameters of both.
    
    """

    # Create a PDF contribution as before
    pdfprofile = Profile()
    pdfparser = PDFParser()
    pdfparser.parseFile(grdata)
    pdfprofile.loadParsedData(pdfparser)
    pdfprofile.setCalculationRange(xmin = 0.1, xmax = 20)

    pdfcontribution = FitContribution("pdf")
    pdfcontribution.setProfile(pdfprofile, xname = "r")

    pdfgenerator = PDFGenerator("G")
    pdfgenerator.setQmax(30.0)
    stru = CreateCrystalFromCIF(file(ciffile))
    pdfgenerator.setPhase(stru)
    pdfgenerator.setQmax(30.0)
    pdfcontribution.addProfileGenerator(pdfgenerator)
    pdfcontribution.setResidualEquation("resv")

    # Create a SAS contribution as well. We assume the nanoparticle is roughly
    # elliptical.
    sasprofile = Profile()
    sasparser = SASParser()
    sasparser.parseFile(iqdata)
    sasprofile.loadParsedData(sasparser)

    sascontribution = FitContribution("sas")
    sascontribution.setProfile(sasprofile)

    from sans.models.EllipsoidModel import EllipsoidModel
    model = EllipsoidModel()
    sasgenerator = SASGenerator("generator", model)
    sascontribution.addProfileGenerator(sasgenerator)
    sascontribution.setResidualEquation("resv")

    # Now we set up the PrCalculator. This is identical to what was done in
    # nppdfsas.py, except we constrain the calculator's iq parameter to the
    # value of I(Q) that is generated by the SASGenerator. 
    prcalculator = PrCalculator("P")
    prcalculator.q.setValue(sasprofile.x)
    prcalculator.diq.setValue(sasprofile.dy)
    # Every time the SASGenerator is called to calculate the profile, it
    # updates the "ycpar" Parameter of the SAS profile. This must have an
    # initial value, so we evaluate the residual of the SAS contribution to
    # make sure that it does.
    sascontribution.residual()
    prcalculator.constrain("iq", sasprofile.ycpar)

    pdfcontribution.registerCalculator(prcalculator)
    pdfcontribution.setEquation("P/(4 * pi * r**2) * G")

    # Moving on
    recipe = FitRecipe()
    recipe.addContribution(pdfcontribution)
    recipe.addContribution(sascontribution)

    # PDF
    phase = pdfgenerator.phase
    lattice = phase.getLattice()
    recipe.addVar(lattice.a)
    Biso = recipe.newVar("Biso", 0.5)
    for scatterer in phase.getScatterers():
        recipe.constrain(scatterer.Biso, Biso)

    recipe.addVar(pdfgenerator.scale, 1)
    recipe.addVar(pdfgenerator.delta2, 0)

    # SAS
    recipe.addVar(sasgenerator.scale, 1, name = "iqscale")
    recipe.addVar(sasgenerator.radius_a, 10)
    recipe.addVar(sasgenerator.radius_b, 10)

    return recipe

def fitRecipe(recipe):
    """We refine in stages to help the refinement converge."""

    # Tune SAS.
    recipe.setWeight(recipe.pdf, 0)
    recipe.fixAll()
    recipe.freeVar("iqscale", value = 1e8)
    recipe.freeVar("radius_a")
    recipe.freeVar("radius_b")
    scipyOptimize(recipe)

    # Tune PDF
    recipe.setWeight(recipe.pdf, 1)
    recipe.setWeight(recipe.sas, 0)
    recipe.fixAll()
    recipe.freeVar("a")
    recipe.freeVar("Biso")
    recipe.freeVar("scale")
    recipe.freeVar("delta2")
    scipyOptimize(recipe)

    # Tune all
    recipe.setWeight(recipe.pdf, 1)
    recipe.setWeight(recipe.sas, 1)
    recipe.freeAll()
    scipyOptimize(recipe)

    return

if __name__ == "__main__":

    ciffile = "data/pb.cif"
    grdata = "data/pb_100_qmin1.gr"
    iqdata = "data/pb_100_qmax1.1.iq"

    recipe = makeRecipe(ciffile, grdata, iqdata)
    recipe.fithook.verbose = 3
    fitRecipe(recipe)

    res = FitResults(recipe)
    res.printResults()

    plotResults(recipe)

# End of file
