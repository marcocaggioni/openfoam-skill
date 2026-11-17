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

Class
    Foam::viscosityModels::threeComponent

Description
    Three-component (TC) non-Newtonian viscosity model (Marco, Nov 17):

        tau = sigma_y + sigma_y*sqrt(gamma_dot/gamma_dot_c)
              + eta_bg*gamma_dot

    with sigma_y = 70 Pa, gamma_dot_c = 100 1/s, eta_bg = 0.05 Pa.s
    (50 cP), rho = 1000 kg/m3. In the kinematic form OpenFOAM uses
    (nu = eta/rho, strain rate sr = gamma_dot):

        nu = min(nuMax, (tau0 + k*sqrt(sr) + nuBg*sr) / sr)

        tau0 = sigma_y/rho            = 0.07      m2/s2
        k    = sigma_y/sqrt(gamma_dot_c)/rho = 0.007 m2/s
        nuBg = eta_bg/rho             = 5e-05     m2/s

    REGULARIZATION: nu diverges as sr -> 0, so it is capped at nuMax:

        nuMax = nu(gamma_dot_reg), gamma_dot_reg = 1e-3 1/s
              = (70 + 70/sqrt(1e-3*100) + 0.05*1e-3)/1000
              = 70.22141 m2/s   (eta_max = 70221.41 Pa.s)

    The cap only bites where gamma_dot < 1e-3 1/s, i.e. deep inside the
    unyielded plug, where the true model has gamma_dot = 0 and the
    exact viscosity is infinite. The yielded region, which carries the
    torque, is unaffected; the plug creeps at ~tau/eta_max ~ 1e-3 1/s
    instead of sitting exactly still.

    This is NOT Herschel-Bulkley (tau = tau0 + K*gamma_dot^n) and not
    any other built-in model: the sqrt(gamma_dot) term is the TC
    model's second component, and no built-in model has it.

SourceFiles
    threeComponent.C

\*---------------------------------------------------------------------------*/

#ifndef threeComponent_H
#define threeComponent_H

#include "viscosityModel.H"
#include "dimensionedScalar.H"
#include "volFields.H"

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

namespace Foam
{
namespace viscosityModels
{

/*---------------------------------------------------------------------------*\
                       Class threeComponent Declaration
\*---------------------------------------------------------------------------*/

class threeComponent
:
    public viscosityModel
{
    // Private data

        dictionary threeComponentCoeffs_;

        dimensionedScalar tau0_;   // sigma_y/rho, m2/s2
        dimensionedScalar k_;      // sigma_y/sqrt(gamma_dot_c)/rho, m2/s
        dimensionedScalar nuBg_;   // eta_bg/rho, m2/s
        dimensionedScalar nuMax_;  // viscosity cap, m2/s


protected:

    // Protected data

        volScalarField nu_;


    // Protected Member Functions

        //- Calculate and return the laminar viscosity
        tmp<volScalarField> calcNu() const;


public:

    //- Runtime type information
    TypeName("threeComponent");


    // Constructors

        //- Construct from components
        threeComponent
        (
            const word& name,
            const dictionary& viscosityProperties,
            const volVectorField& U,
            const surfaceScalarField& phi
        );


    //- Destructor
    virtual ~threeComponent() = default;


    // Member Functions

        //- Return the laminar viscosity
        virtual tmp<volScalarField> nu() const
        {
            return nu_;
        }

        //- Return the laminar viscosity for patch
        virtual tmp<scalarField> nu(const label patchi) const
        {
            return nu_.boundaryField()[patchi];
        }

        //- Correct the laminar viscosity
        virtual void correct()
        {
            nu_ = calcNu();
        }

        //- Read transportProperties dictionary
        virtual bool read(const dictionary& viscosityProperties);
};


// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

} // End namespace viscosityModels
} // End namespace Foam

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

#endif

// ************************************************************************* //
