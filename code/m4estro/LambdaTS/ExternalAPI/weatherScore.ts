import { Code } from "aws-cdk-lib/aws-lambda";


interface WeatherScore {
    Code:string
    Italian_Description:string;
    English_Description:string;
    Score:number;
}



export const weatherData:WeatherScore[] = [
        {
            Code: "type_43",
            Italian_Description: "Sereno",
            English_Description: "Clear",
            Score: 0.00
        },
        {
            Code: "type_42",
            Italian_Description: "Parzialmente nuvoloso",
            English_Description: "Partially Cloudy",
            Score: 0.00
        },
        {
            Code: "type_41",
            Italian_Description: "Nuvoloso",
            English_Description: "Overcast",
            Score: 0.00 
        },
        {
            Code: "type_29",
            Italian_Description: "Nuvolosità invariata",
            English_Description: "Sky Unchanged",
            Score: 0.00
        },
        {
            Code: "type_28",
            Italian_Description: "Aumento della nuvolosità / Copertura in aumento",
            English_Description: "Sky Coverage Increasing",
            Score: 0.00
        },
        {
            Code: "type_27",
            Italian_Description: "Diminuzione della nuvolosità / Copertura in diminuzione",
            English_Description: "Sky Coverage Decreasing",
            Score: 0.00
        },
        {
            Code: "type_26",
            Italian_Description: "Pioggia leggera",
            English_Description: "Light Rain",
            Score: 0.25
        },
        {
            Code: "type_2",
            Italian_Description: "Pioviggine",
            English_Description: "Drizzle",
            Score: 0.25
        },
        {
            Code: "type_4",
            Italian_Description: "Pioviggine debole",
            English_Description: "Light Drizzle",
            Score: 0.25
        },
        {
            Code: "type_39",
            Italian_Description: "Polvere di diamanti",
            English_Description: "Diamond Dust",
            Score: 0.25
        },
        {
            Code: "type_20",
            Italian_Description: "Precipitazioni nelle vicinanze",
            English_Description: "Precipitation In Vicinity",
            Score: 0.25
        },
        {
            Code: "type_6",
            Italian_Description: "Pioviggine debole / Pioggia",
            English_Description: "Light Drizzle/Rain",
            Score: 0.25
        },
        {
            Code:"type_35",
            Italian_Description:"Neve leggera",
            English_Description:"Light Snow",
            Score:0.50
        },
        {
            Code:"type_24",
            Italian_Description:"Rovesci di pioggia",
            English_Description:"Rain Showers",
            Score:0.50
        },
        {
            Code:"type_21",
            Italian_Description:"Pioggia",
            English_Description:"Rain",
            Score:0.50
        },
        {
            Code:"type_17",
            Italian_Description:"Ghiaccio",
            English_Description:"Ice",
            Score:0.50
        },
        {
            Code:"type_14",
            Italian_Description:"Pioggia gelata debole",
            English_Description:"Light Freezing Rain",
            Score:0.50
        },
        {
            Code:"type_11",
            Italian_Description:"Pioviggine gelata debole / Pioggia gelata",
            English_Description:"Light Freezing Drizzle/Freezing Rain",
            Score:0.50
        },
        {
            Code:"type_9",
            Italian_Description:"Pioviggine gelata / Pioggia gelata",
            English_Description:"Freezing Drizzle/Freezing Rain",
            Score:0.50
        },
        {
            Code:"type_23",
            Italian_Description:"Pioggia debole e neve",
            English_Description:"Light Rain And Snow",
            Score:0.50
        },
        {
            Code:"type_30",
            Italian_Description:"Fumo o foschia",
            English_Description:"Smoke Or Haze",
            Score:0.50
        },
        {
            Code:"type_8",
            Italian_Description:"Nebbia",
            English_Description:"Fog",
            Score:0.50
        },
        {
          Code: "type_19",
          Italian_Description: "Foschia",
          English_Description: "Mist",
          Score: 0.75
        },
        {
            Code:"type_12",
            Italian_Description:"Nebbia gelata",
            
            English_Description:"Freezing Fog",
            Score:0.75
        },
        {
            Code:"type_32",
            Italian_Description:"Rovesci di pioggia e neve",
            English_Description:"Snow And Rain Showers",
            Score:0.75
        },
        {
            Code:"type_33",
            Italian_Description:"Rovesci di neve",
            
            English_Description:"Snow Showers",
            Score:0.75
        },
        {
            Code:"type_31",
            Italian_Description:"Neve",
            English_Description:"Snow",
            Score:0.75
        },
        {
            Code:"type_5",
            Italian_Description:"Pioviggine intensa / Pioggia",
            English_Description:"Heavy Drizzle/Rain",
            Score:0.75
        },
        {
            Code: "type_3",
            Italian_Description: "Pioviggine intensa",
            English_Description: "Heavy Drizzle",
            Score: 0.75
        },
        {
            Code: "type_25",
            Italian_Description: "Pioggia intensa", 
            
            English_Description: "Heavy Rain",
            Score: 0.75
        },
    {
        Code: "type_1",
        Italian_Description: "Neve che soffia o viene trasportata",
        English_Description: "Blowing Or Drifting Snow",
        Score: 0.75
    },
    {
        Code:'type_22',
        Italian_Description:'Pioggia intensa e neve',
        English_Description:'Heavy Rain And Snow',
        Score:1.00

    },
    {
        
        Code: "type_34",
        Italian_Description: "Forti nevicate",
        English_Description: "Heavy Snow",
        Score: 1.00
    },
    {
        Code: "type_10",
        Italian_Description: "Pioviggine gelata intensa / Pioggia gelata",
        English_Description: "Heavy Freezing Drizzle/Freezing Rain",
        Score: 1.00
    },
    {
        Code: "type_13",
        Italian_Description: "Pioggia gelata intensa",
        English_Description: "Heavy Freezing Rain",
        Score: 1.00
    },
    {
        Code: "type_40",
        Italian_Description: "Grandine",
        English_Description: "Hail",
        Score: 1.00
    },
    {
        Code: "type_16",
        Italian_Description: "Grandinate",
        English_Description: "Hail Showers",
        Score: 1.00
    },
    {
        Code: "type_7",
        Italian_Description: "Tempesta di polvere",
        English_Description: "Dust Storm",
        Score: 1.00
    },
    {
        Code: "type_36",
        Italian_Description: "Burrasca",
        English_Description: "Squalls",
        Score: 1.00
    },
    {
        Code: "type_38",
        Italian_Description: "Temporale senza precipitazione",
        English_Description: "Thunderstorm Without Precipitation",
        Score: 1.00
    },
    {
        Code: "type_37",
        Italian_Description: "Temporale",
        English_Description: "Thunderstorm",
        Score: 1.00
    },
    {
        Code:"type_18",
        Italian_Description:"Fulmini senza tuoni",
        
        English_Description:"Lightning Without Thunder",
        Score:1.00
    },
    {
        
        Code:"type_15",
        
        Italian_Description:"Nube a imbuto / Tornado",
        
        English_Description:"Funnel Cloud/Tornado",
        
        Score:1.00
    }

    ];


    export function getWeatherScore(code: string): number {
        const weather = weatherData.find(item => item.Code === code);
        if (!weather) {
            throw new Error(`Weather code ${code} not found`);
        }
        return  weather.Score;
    }