/*---------------------------------------------------------------------------*\
  =========                 |
  \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\    /   O peration     |
    \\  /    A nd           | www.openfoam.com
     \\/     M anipulation  |
-------------------------------------------------------------------------------
    Copyright (C) 2026 Marco Caggioni
-------------------------------------------------------------------------------
License
    This file is part of the openfoam-skill repository (MIT licence).
    It is derived from the OpenFOAM HerschelBulkley viscosity model
    (GPL, Copyright (C) 2011-2019 OpenFOAM Foundation / OpenCFD Ltd.),
    whose structure it follows; the constitutive law is different.
    See threeComponent.H for the model and the regularization.
\*---------------------------------------------------------------------------*/

#include "threeComponent.H"
#include "addToRunTimeSelectionTable.H"
#include "surfaceFields.H"

// * * * * * * * * * * * * * Static Data Members * * * * * * * * * * * * * //

namespace Foam
{
namespace viscosityModels
{
    defineTypeNameAndDebug(threeComponent, 0);

    addToRunTimeSelectionTable
    (
        viscosityModel,
        threeComponent,
        dictionary
    );
}
}


// * * * * * * * * * * * Protected Member Functions  * * * * * * * * * * * //

Foam::tmp<Foam::volScalarField>
Foam::viscosityModels::threeComponent::calcNu() const
{
    dimensionedScalar tone("tone", dimTime, 1.0);
    dimensionedScalar rtone("rtone", dimless/dimTime, 1.0);

    tmp<volScalarField> sr(strainRate());

    // nu = min(nuMax, (tau0 + k*sqrt(sr) + nuBg*sr) / max(sr, VSMALL))
    // The k term follows the HerschelBulkley dimensional trick:
    // k [m2/s] * rtone [1/s] * sqrt(tone*sr) [dimensionless] = m2/s2.
    return
    (
        min
        (
            nuMax_,
            (
                tau0_
              + k_*rtone*sqrt(tone*sr())
              + nuBg_*sr()
            )
           /max(sr(), dimensionedScalar ("VSMALL", dimless/dimTime, VSMALL))
        )
    );
}


// * * * * * * * * * * * * * * * * Constructors  * * * * * * * * * * * * * * //

Foam::viscosityModels::threeComponent::threeComponent
(
    const word& name,
    const dictionary& viscosityProperties,
    const volVectorField& U,
    const surfaceScalarField& phi
)
:
    viscosityModel(name, viscosityProperties, U, phi),
    threeComponentCoeffs_
    (
        viscosityProperties.optionalSubDict(typeName + "Coeffs")
    ),
    tau0_("tau0", dimViscosity/dimTime, threeComponentCoeffs_),
    k_("k", dimViscosity, threeComponentCoeffs_),
    nuBg_("nuBg", dimViscosity, threeComponentCoeffs_),
    nuMax_("nuMax", dimViscosity, threeComponentCoeffs_),
    nu_
    (
        IOobject
        (
            name,
            U_.time().timeName(),
            U_.db(),
            IOobject::NO_READ,
            IOobject::AUTO_WRITE
        ),
        calcNu()
    )
{}


// * * * * * * * * * * * Member Functions  * * * * * * * * * * * * * * //

bool Foam::viscosityModels::threeComponent::read
(
    const dictionary& viscosityProperties
)
{
    viscosityModel::read(viscosityProperties);

    threeComponentCoeffs_ =
        viscosityProperties.optionalSubDict(typeName + "Coeffs");

    threeComponentCoeffs_.readEntry("tau0", tau0_);
    threeComponentCoeffs_.readEntry("k", k_);
    threeComponentCoeffs_.readEntry("nuBg", nuBg_);
    threeComponentCoeffs_.readEntry("nuMax", nuMax_);

    return true;
}


// ************************************************************************* //
