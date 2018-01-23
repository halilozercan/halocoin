import React, { Component } from 'react';
import {MCardStats} from '../components/card.js';
import axios from 'axios';
import LinearProgress from 'material-ui/LinearProgress';
import {Card, CardActions, CardHeader, CardMedia, CardTitle, CardText} from 'material-ui/Card';
import Avatar from 'material-ui/Avatar';
import FlatButton from 'material-ui/FlatButton';
import FontIcon from 'material-ui/FontIcon';
import {red500, green500} from 'material-ui/styles/colors';

class Power extends Component {
  constructor(props) {
    super(props);
    this.state = {
      'status': 'Loading...',
      'available': 'Loading...'
    }
    this.props.socket.on('power_status', (socket) => {
      this.update();
    });
  }

  componentWillMount() {
    this.update();
  }

  update() {
    axios.get('/power_available').then((response) => {
      if(response.data.success) {
        this.setState({
          available: 'Power service is ready!'
        })
      }
      else{
        this.setState({
          available: response.data.message
        })
      }
    }).catch((error) => {
      this.setState({
        available: 'Power service is currently unavailable'
      })
    });
    axios.get("/status_power").then((response) => {
      let data = response.data;
      this.setState((state) => {
        state['status'] = data.status;
        return state;
      });
    });
  }

  render() {
    return (
      <Card>
        <CardHeader
          title="Power Status"
          subtitle={this.state.available}
          avatar={<Avatar backgroundColor={green500} icon={<FontIcon className="material-icons">whatshot</FontIcon>} />}
        />
        <CardActions style={{ width: '100%', textAlign: 'right' }}>
          <FlatButton label={this.state.status} disabled={true}/>
        </CardActions>
      </Card>
    );
  }
}

export default Power;
/*
<div className="col-lg-6 col-md-6 col-sm-6">
        <div className="card card-stats">
          <div className="card-header" data-background-color="green">
            <i className="material-icons">whatshot</i>
          </div>
          <div className="card-content">
            <p className="category">Power Status</p>
            <h3 className="title">{this.state.status}</h3>
          </div>
          <div className="card-footer">
            <div className="stats">
              <i className="material-icons">local_offer</i> Updated now!
            </div>
          </div>
        </div>
      </div>
      */