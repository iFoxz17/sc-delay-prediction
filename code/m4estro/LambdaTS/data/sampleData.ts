export const sampleCarriersData = [
    {
        name: "FedEx",
        tracking_url: "https://www.fedex.com/apps/fedextrack/?tracknumbers={tracking_number}",
        api_key: "fedex_api_key",

    },
    {
  
        name: "UPS",
        tracking_url: "https://www.ups.com/track?loc=en_US&tracknum={tracking_number}&requester=ST/",
        api_key: "ups_api_key",

    },
    {
      
        name: "USPS",
        tracking_url: "https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_number}",
        api_key: "usps_api_key",

    },
    {
  
        name: "DHL Express",
        tracking_url: "https://www.dhl.com/en/express/tracking.html?AWB={tracking_number}",
        api_key: "dhl_api_key",

    },
    {
 
        name: "Local Courier",
        tracking_url: "https://example-local-courier.com/track?id={tracking_number}",
        api_key: "local_courier_api_key",

    }
];

// Sample data conforming to the schema (20 entries)
 export const sampleSuppliersData = [
    {
       supplier_name: "Global Exports Inc.", // Note: Typo 'comapny'
        location: "1 Trade Center Plaza, New York",
        city: "New York",
        state: "NY",
        country_name: "United States",
        CALI: 0.88
    },
    {
       supplier_name: "Maple Solutions Ltd.", // Note: Typo 'comapny'
        location: "Suite 500, 1 King St W, Toronto",
        city: "Toronto",
        state: "ON",
        country_name: "Canada",
        CALI: 0.75
    },
    {
       supplier_name: "EuroTech Components", // Note: Typo 'comapny'
        location: "Industriestrasse 10, Munich",
        city: "Munich",
        state: "Bavaria", // State can be string
        country_name: "Germany",
    },
    {
       supplier_name: "Seine Innovations", // Note: Typo 'comapny'
        location: "5 Rue de Rivoli, Paris",
        city: "Paris",
        // state is optional, omitted here
        country_name: "France",
        CALI: 0.72
    },
    {
       supplier_name: "London Financial Group", // Note: Typo 'comapny'
        location: "1 Canary Wharf, London",
        city: "London",
        state: null, // state is nullable
        country_name: "United Kingdom",
        CALI: 0.95
    },
    {
       supplier_name: "Rising Sun Electronics", // Note: Typo 'comapny'
        location: "Akihabara District, Tokyo",
        city: "Tokyo",
        // state is optional, omitted here
        country_name: "Japan",
        CALI: 0.80
    },
    {
       supplier_name: "Dragon Manufacturing", // Note: Typo 'comapny'
        location: "Guangdong Industrial Zone",
        // city is optional, omitted here
        state: "Guangdong",
        country_name: "China",
        CALI: 0.40
    },
    {
       supplier_name: "Singapore Hub Services", // Note: Typo 'comapny'
        location: "Marina Bay Sands Tower 1",
        city: "Singapore",
        state: null, // state can be null (city-state)
        country_name: "Singapore",
        CALI: 0.98
    },
    {
       supplier_name: "Bangalore Software Labs", // Note: Typo 'comapny'
        location: "Electronic City, Phase 1, Bangalore",
        city: "Bangalore",
        state: "Karnataka",
        country_name: "India",
        CALI: 0.60
    },
    {
       supplier_name: "Andes Mining Corp", // Note: Typo 'comapny'
        location: "Avenida Apoquindo 3000, Santiago",
        city: "Santiago",
        state: "Metropolitana",
        country_name: "Chile",
        CALI: 0.25
    },
    {
       supplier_name: "Amazonian Resources", // Note: Typo 'comapny'
        location: "Manaus Free Trade Zone",
        city: "Manaus",
        state: "Amazonas",
        country_name: "Brazil",
        CALI: 0.15
    },
    {
       supplier_name: "Mexico City Logistics", // Note: Typo 'comapny'
        location: "Reforma 222, Mexico City",
        city: "Mexico City",
        state: "CDMX",
        country_name: "Mexico",
        CALI: 0.55
    },
    {
       supplier_name: "Nairobi Tech Ventures", // Note: Typo 'comapny'
        location: "Westlands Business Park, Nairobi",
        city: "Nairobi",
        // state optional, omitted
        country_name: "Kenya",
        CALI: 0.30
    },
    {
       supplier_name: "Lagos Trading Co.", // Note: Typo 'comapny'
        location: "Victoria Island, Lagos",
        city: "Lagos",
        state: "Lagos State",
        country_name: "Nigeria",
        CALI: 0.20
    },
    {
       supplier_name: "Cape Agri Products", // Note: Typo 'comapny'
        location: "Stellenbosch Farms",
        // city optional, omitted
        state: "Western Cape",
        country_name: "South Africa",
    },
    {
       supplier_name: "Outback Mining Ltd.", // Note: Typo 'comapny'
        location: "Perth CBD",
        city: "Perth",
        state: "WA",
        country_name: "Australia",
        CALI: 0.50
    },
    {
       supplier_name: "Kiwi Innovations", // Note: Typo 'comapny'
        location: "Auckland Waterfront",
        city: "Auckland",
        state: null, // state can be null
        country_name: "New Zealand",
        CALI: 0.70
    },
    {
       supplier_name: "Alpine Precision", // Note: Typo 'comapny'
        location: "Zurich Technopark",
        city: "Zurich",
        state: "ZH", // Canton code
        country_name: "Switzerland",
        CALI: 1.0 // Edge case CALI
    },
    {
       supplier_name: "Nordic Consulting", // Note: Typo 'comapny'
        location: "Stockholm City Center",
        city: "Stockholm",
        // state optional, omitted
        country_name: "Sweden",
        CALI: 0.90
    },
    {
       supplier_name: "Desert Ventures LLC", // Note: Typo 'comapny'
        location: "Dubai Silicon Oasis",
        city: "Dubai",
        state: "Dubai", // Emirate
        country_name: "United Arab Emirates",
        CALI: 0.0 // Edge case CALI
    }
];



export const sampleCountriesData = [
    {
        name: "United States",
        total_holidays: 11, // Approximate federal holidays
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "Canada",
        total_holidays: 10, // Varies by province
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "Mexico",
        total_holidays: 7, // Official public holidays
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "United Kingdom",
        total_holidays: 8, // Bank holidays (varies slightly)
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "Germany",
        total_holidays: 9, // Varies significantly by state
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "France",
        total_holidays: 11,
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "Japan",
        total_holidays: 16,
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "Australia",
        total_holidays: 10, // Varies by state/territory
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "Brazil",
        total_holidays: 12, // National holidays, varies locally
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "India",
        total_holidays: 18, // Highly variable (central + state + restricted)
        weekend_start: "Saturday", // Most common, Sunday often official holiday
        weekend_end: "Sunday"
    },
    {
        name: "South Korea",
        total_holidays: 15,
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "Italy",
        // total_holidays is optional, omitted here
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "Spain",
        total_holidays: 14, // National + regional
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "Saudi Arabia",
        total_holidays: 5, // Mainly Eid holidays
        weekend_start: "Friday",
        weekend_end: "Saturday"
    },
    {
        name: "United Arab Emirates",
        total_holidays: 14,
        weekend_start: "Saturday", // Changed recently
        weekend_end: "Sunday"    // Changed recently
    },
    {
        name: "Israel",
        total_holidays: 9, // Official public holidays
        weekend_start: "Friday", // Starts Friday afternoon
        weekend_end: "Saturday"
    },
    {
        name: "Egypt",
        total_holidays: 13,
        weekend_start: "Friday",
        weekend_end: "Saturday"
    },
    {
        name: "Nigeria",
        total_holidays: 11,
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "South Africa",
        total_holidays: 12,
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "Argentina",
        total_holidays: 19, // Includes bridge holidays
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "China",
        total_holidays: 7, // Official, but complex system with makeup days
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "Russia",
        total_holidays: 14,
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "Switzerland",
        total_holidays: null, // total_holidays is nullable
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "Singapore",
        total_holidays: 11,
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "New Zealand",
        total_holidays: 11,
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "Turkey",
        total_holidays: 14,
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "Thailand",
        total_holidays: 16,
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "Vietnam",
        total_holidays: 11,
        weekend_start: "Saturday",
        weekend_end: "Sunday"   
    },
    {
        name:'Chile',
        total_holidays: 16,
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name:'Kenya',
        total_holidays: 12,
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    {
        name: "Philippines",
        total_holidays: 18,
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    },
    { 
        name: "Sweden",
        total_holidays: 13, // Approximate public holidays
        weekend_start: "Saturday",
        weekend_end: "Sunday"
    }

];



