export type Weekday =
  | 'Monday' | 'Tuesday' | 'Wednesday'
  | 'Thursday' | 'Friday' | 'Saturday' | 'Sunday';

export interface CountryWeekend {
  countryCode: string;    
  countryName: string;
  weekendDays: Weekday[];
}


export const exceptionalWeekends: CountryWeekend[] = [
  // Friday & Saturday weekends
  { countryCode: 'DZ', countryName: 'Algeria',      weekendDays: ['Friday', 'Saturday'] },
  { countryCode: 'AF', countryName: 'Afghanistan',  weekendDays: ['Friday', 'Saturday'] },
  { countryCode: 'BH', countryName: 'Bahrain',       weekendDays: ['Friday', 'Saturday'] },
  { countryCode: 'BD', countryName: 'Bangladesh',    weekendDays: ['Friday', 'Saturday'] },
  { countryCode: 'EG', countryName: 'Egypt',         weekendDays: ['Friday', 'Saturday'] },
  { countryCode: 'IL', countryName: 'Israel',        weekendDays: ['Friday', 'Saturday'] },
  { countryCode: 'IQ', countryName: 'Iraq',          weekendDays: ['Friday', 'Saturday'] },
  { countryCode: 'JO', countryName: 'Jordan',        weekendDays: ['Friday', 'Saturday'] },
  { countryCode: 'KW', countryName: 'Kuwait',        weekendDays: ['Friday', 'Saturday'] },
  { countryCode: 'LY', countryName: 'Libya',         weekendDays: ['Friday', 'Saturday'] },
  { countryCode: 'MY', countryName: 'Malaysia',      weekendDays: ['Friday', 'Saturday'] },
  { countryCode: 'MV', countryName: 'Maldives',      weekendDays: ['Friday', 'Saturday'] },
  { countryCode: 'OM', countryName: 'Oman',          weekendDays: ['Friday', 'Saturday'] },
  { countryCode: 'PS', countryName: 'Palestine',     weekendDays: ['Friday', 'Saturday'] },
  { countryCode: 'QA', countryName: 'Qatar',         weekendDays: ['Friday', 'Saturday'] },
  { countryCode: 'SA', countryName: 'Saudi Arabia',  weekendDays: ['Friday', 'Saturday'] },
  { countryCode: 'SD', countryName: 'Sudan',         weekendDays: ['Friday', 'Saturday'] },
  { countryCode: 'SY', countryName: 'Syria',         weekendDays: ['Friday', 'Saturday'] },
  { countryCode: 'YE', countryName: 'Yemen',         weekendDays: ['Friday', 'Saturday'] },
  { countryCode: 'BN', countryName: 'Brunei Darussalam', weekendDays: ['Friday', 'Sunday'] },
  { countryCode: 'DJ', countryName: 'Djibouti',      weekendDays: ['Friday'] },
  { countryCode: 'IR', countryName: 'Iran',          weekendDays: ['Friday'] },
  { countryCode: 'SO', countryName: 'Somalia',       weekendDays: ['Friday'] }, 
  { countryCode: 'NP', countryName: 'Nepal',         weekendDays: ['Saturday'] },
  { countryCode: 'MX', countryName: 'Mexico',        weekendDays: ['Sunday'] },
  { countryCode: 'CO', countryName: 'Colombia',      weekendDays: ['Sunday'] },
  { countryCode: 'UG', countryName: 'Uganda',        weekendDays: ['Sunday'] },
  { countryCode: 'ER', countryName: 'Eritrea',       weekendDays: ['Sunday'] },
  { countryCode: 'IN', countryName: 'India',         weekendDays: ['Sunday'] },
  { countryCode: 'PH', countryName: 'Philippines',   weekendDays: ['Sunday'] },
  { countryCode: 'GQ', countryName: 'Equatorial Guinea', weekendDays: ['Sunday'] },
];
