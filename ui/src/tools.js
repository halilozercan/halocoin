import axios from 'axios';

export const timestampToDatetime = (timestamp) => {
    var date = new Date(timestamp*1000);
    var formattedTime = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    return formattedTime;
}

export const axiosInstance = axios.create({
  baseURL: 'http://0.0.0.0:7001'
});

export const getColor = (value, lum) => {
  //value from 0 to 100
  value = value/100;
  var hue=((1-value)*120).toString(10);
  return ["hsl(",hue,",100%,",lum,"%)"].join("");
}

axios.defaults.baseURL = 'http://0.0.0.0:7001';